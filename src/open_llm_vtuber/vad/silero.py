import asyncio
from collections import deque
from enum import Enum

import numpy as np
import torch
from loguru import logger
from pydantic import BaseModel
from silero_vad import load_silero_vad

from .vad_interface import VADInterface


class SileroVADConfig(BaseModel):
    orig_sr: int = 16000
    target_sr: int = 16000
    prob_threshold: float = 0.4
    db_threshold: int = 60
    required_hits: int = 3  # 3 * (0.032) = 0.1s
    required_misses: int = 24  # 24 * (0.032) = 0.8s
    smoothing_window: int = 5


class VADEngine(VADInterface):
    def __init__(
        self,
        orig_sr: int = 16000,
        target_sr: int = 16000,
        prob_threshold: float = 0.4,
        db_threshold: int = 60,
        required_hits: int = 3,
        required_misses: int = 24,
        smoothing_window: int = 5,
    ):
        self.config = SileroVADConfig(
            orig_sr=orig_sr,
            target_sr=target_sr,
            prob_threshold=prob_threshold,
            db_threshold=db_threshold,
            required_hits=required_hits,
            required_misses=required_misses,
            smoothing_window=smoothing_window,
        )
        self.model = self.load_vad_model()
        self.state = StateMachine(self.config)
        self.window_size_samples = 512 if self.config.target_sr == 16000 else 256
        # 512 / 16000 = 0.032s

    def load_vad_model(self):
        logger.info("Loading Silero-VAD model...")
        return load_silero_vad()

    def detect_speech(self, audio_data: list[float]):
        audio_np = np.array(audio_data, dtype=np.float32)
        for i in range(0, len(audio_np), self.window_size_samples):
            chunk_np = audio_np[i : i + self.window_size_samples]
            if len(chunk_np) < self.window_size_samples:
                break
            chunk = torch.Tensor(chunk_np)

            with torch.no_grad():
                speech_prob = self.model(chunk, self.config.target_sr).item()

            if speech_prob:
                # print(speech_prob)
                iter = self.state.get_result(speech_prob, chunk_np)

                for probs, dbs, chunk in iter:  # detected a sequence of voice bytes
                    # rounded_probs = [round(x, 2) for x in probs]
                    # rounded_dbs = [round(y, 2) for y in dbs]

                    audio_chunk = bytes(chunk)
                    yield audio_chunk

        del audio_np


# Define state enumeration
class State(Enum):
    IDLE = 1  # Idle state, waiting for speech
    ACTIVE = 2  # Speech detection state
    INACTIVE = 3  # Speech end state (silence state)


class StateMachine:
    def __init__(self, config: SileroVADConfig):
        self.state = State.IDLE
        self.prob_threshold = config.prob_threshold
        self.db_threshold = config.db_threshold
        self.required_hits = config.required_hits
        self.required_misses = config.required_misses
        self.smoothing_window = config.smoothing_window

        self.probs = []
        self.dbs = []
        self.bytes = bytearray()
        self.miss_count = 0
        self.hit_count = 0

        self.prob_window = deque(maxlen=self.smoothing_window)
        self.db_window = deque(maxlen=self.smoothing_window)

        self.pre_buffer = deque(maxlen=20)

    @classmethod
    def calculate_db(cls, audio_data: np.ndarray) -> float:
        rms = np.sqrt(np.mean(np.square(audio_data)))
        return 20 * np.log10(rms + 1e-7) if rms > 0 else -np.inf

    def update(self, chunk_bytes, prob, db):
        self.probs.append(prob)
        self.dbs.append(db)
        self.bytes.extend(chunk_bytes)

    def reset_buffers(self):
        self.probs.clear()
        self.dbs.clear()
        self.bytes.clear()

    def get_smoothed_values(self, prob, db):
        self.prob_window.append(prob)
        self.db_window.append(db)
        smoothed_prob = np.mean(self.prob_window)
        smoothed_db = np.mean(self.db_window)
        return smoothed_prob, smoothed_db

    def process(self, prob, float_chunk_np: np.ndarray):
        int_chunk_np = float_chunk_np * 32767
        chunk_bytes = int_chunk_np.astype(np.int16).tobytes()
        db = self.calculate_db(int_chunk_np)

        # Obtain the smoothed prob and db
        smoothed_prob, smoothed_db = self.get_smoothed_values(prob, db)

        if self.state == State.IDLE:
            self.pre_buffer.append(chunk_bytes)
            if (
                smoothed_prob >= self.prob_threshold
                and smoothed_db >= self.db_threshold
            ):
                self.hit_count += 1
                if self.hit_count >= self.required_hits:
                    self.state = State.ACTIVE
                    self.update(chunk_bytes, smoothed_prob, smoothed_db)
                    self.hit_count = 0
                    yield [], [], b"<|PAUSE|>"
            else:
                self.hit_count = 0

        elif self.state == State.ACTIVE:
            self.update(chunk_bytes, smoothed_prob, smoothed_db)
            if (
                smoothed_prob >= self.prob_threshold
                and smoothed_db >= self.db_threshold
            ):
                self.miss_count = 0
            else:
                self.miss_count += 1
                if self.miss_count >= self.required_misses:
                    self.state = State.INACTIVE
                    self.miss_count = 0

        elif self.state == State.INACTIVE:
            self.update(chunk_bytes, smoothed_prob, smoothed_db)
            if (
                smoothed_prob >= self.prob_threshold
                and smoothed_db >= self.db_threshold
            ):
                self.hit_count += 1
                if self.hit_count >= self.required_hits:
                    self.state = State.ACTIVE
                    self.hit_count = 0
                    self.miss_count = 0
            else:
                self.hit_count = 0
                self.miss_count += 1
                if self.miss_count >= self.required_misses:
                    self.state = State.IDLE
                    self.miss_count = 0
                    yield [], [], b"<|RESUME|>"
                    if len(self.probs) > 30:
                        pre_bytes = b"".join(self.pre_buffer)
                        yield self.probs, self.dbs, pre_bytes + self.bytes
                        self.reset_buffers()
                    self.pre_buffer.clear()

    def get_result(self, input_num, chunk_np):
        yield from self.process(input_num, chunk_np)


async def vad_main():
    global vad, audio_queue
    vad = VADEngine(config=SileroVADConfig())
    audio_queue = asyncio.Queue()
    from tqdm.asyncio import tqdm

    async def data_wrapper(websocket):
        async for chunk in websocket:
            yield chunk

    async def audio_handler(websocket):
        async for chunk in tqdm(data_wrapper(websocket), desc="Audio chunk"):
            # print(len(chunk))
            for _bytes in vad.detect_speech(chunk):
                print(_bytes[:44])
                # await audio_queue.put(_bytes)
                pass

    async def empty_run():
        while True:
            await asyncio.sleep(0.1)

    async def start_websocket_server():
        import websockets

        host = "localhost"
        port = 8765
        start_server = websockets.serve(audio_handler, host, port)
        logger.info(f"WebSocket server started at ws://{host}:{port}")
        await start_server  # run forever until the task is cancelled

    await asyncio.gather(start_websocket_server(), empty_run())
    # await start_playback(audio_queue, sr=vad.config.target_sr)


if __name__ == "__main__":
    asyncio.run(vad_main())
