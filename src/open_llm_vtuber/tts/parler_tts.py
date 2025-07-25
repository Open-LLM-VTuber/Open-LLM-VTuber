from .tts_interface import TTSInterface
import os
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
import torch
import soundfile as sf
from loguru import logger
# uv pip install git+https://github.com/huggingface/parler-tts.git


class ParlerTTSEngine(TTSInterface):
    def __init__(
        self,
        model_name: str = "parler-tts/parler-tts-mini-v1",
        device: str = "auto",
        voice_description: str = "A clear female voice, medium pitch and speed.",
    ):
        if device:
            self.device = device
        else:
            logger.info("parler_tts: Using default device")
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.voice_description = voice_description

        logger.info(f"parler_tts: Using device: {self.device}")
        logger.info(f"parler_tts: Loading model {model_name}")

        self.model = ParlerTTSForConditionalGeneration.from_pretrained(model_name).to(
            self.device
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.sampling_rate = self.model.config.sampling_rate

    def generate_audio(self, text: str, file_name_no_ext=None) -> str:
        output_path = self.generate_cache_file_name(file_name_no_ext, "wav")

        try:
            desc_ids = self.tokenizer(
                self.voice_description, return_tensors="pt"
            ).input_ids.to(self.device)
            prompt_ids = self.tokenizer(text, return_tensors="pt").input_ids.to(
                self.device
            )

            generation = self.model.generate(
                input_ids=desc_ids, prompt_input_ids=prompt_ids
            )
            audio_arr = generation.cpu().numpy().squeeze()

            sf.write(output_path, audio_arr, self.sampling_rate)

            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Output audio not found: {output_path}")

            return output_path

        except Exception as e:
            raise RuntimeError(f"Failed to generate audio with Parler-TTS: {str(e)}")

