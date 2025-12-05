import os
import numpy as np
import sherpa_onnx
from loguru import logger
from .asr_interface import ASRInterface
from .utils import download_and_extract, check_and_extract_local_file
import onnxruntime


class VoiceRecognition(ASRInterface):
    def __init__(
        self,
        model_type: str = "paraformer",  # or "transducer", "nemo_ctc", "wenet_ctc", "whisper", "tdnn_ctc", "sense_voice"
        encoder: str = None,  # Path to the encoder model, used with transducer
        decoder: str = None,  # Path to the decoder model, used with transducer
        joiner: str = None,  # Path to the joiner model, used with transducer
        paraformer: str = None,  # Path to the model.onnx from Paraformer
        nemo_ctc: str = None,  # Path to the model.onnx from NeMo CTC
        wenet_ctc: str = None,  # Path to the model.onnx from WeNet CTC
        tdnn_model: str = None,  # Path to the model.onnx for the tdnn model of the yesno recipe
        whisper_encoder: str = None,  # Path to whisper encoder model
        whisper_decoder: str = None,  # Path to whisper decoder model
        sense_voice: str = None,  # Path to the model.onnx from SenseVoice
        tokens: str = None,  # Path to tokens.txt
        hotwords_file: str = "",  # Path to hotwords file
        hotwords_score: float = 1.5,  # Hotwords score
        modeling_unit: str = "",  # Modeling unit for hotwords
        bpe_vocab: str = "",  # Path to bpe vocabulary, used with hotwords
        num_threads: int = 1,  # Number of threads for neural network computation
        whisper_language: str = "",  # Language for whisper model
        whisper_task: str = "transcribe",  # Task for whisper model (transcribe or translate)
        whisper_tail_paddings: int = -1,  # Tail padding frames for whisper model
        blank_penalty: float = 0.0,  # Penalty for blank symbol
        decoding_method: str = "greedy_search",  # Decoding method (greedy_search or modified_beam_search)
        debug: bool = False,  # Show debug messages
        sample_rate: int = 16000,  # Sample rate
        feature_dim: int = 80,  # Feature dimension
        use_itn: bool = True,  # Use ITN for SenseVoice models
        provider: str = "cpu",  # Provider for inference (cpu or cuda)
    ) -> None:
        self.model_type = model_type
        self.encoder = encoder
        self.decoder = decoder
        self.joiner = joiner
        self.paraformer = paraformer
        self.nemo_ctc = nemo_ctc
        self.wenet_ctc = wenet_ctc
        self.tdnn_model = tdnn_model
        self.whisper_encoder = whisper_encoder
        self.whisper_decoder = whisper_decoder
        self.sense_voice: str = sense_voice
        self.tokens = tokens
        self.hotwords_file = hotwords_file
        self.hotwords_score = hotwords_score
        self.modeling_unit = modeling_unit
        self.bpe_vocab = bpe_vocab
        self.num_threads = num_threads
        self.whisper_language = whisper_language
        self.whisper_task = whisper_task
        self.whisper_tail_paddings = whisper_tail_paddings
        self.blank_penalty = blank_penalty
        self.decoding_method = decoding_method
        self.debug = debug
        self.SAMPLE_RATE = sample_rate
        self.feature_dim = feature_dim
        self.use_itn = use_itn

        # we need to find a way to get cuda version of sherpa-onnx before we can
        # use the gpu provider.
        self.provider = provider
        if self.provider == "cuda":
            try:
                if "CUDAExecutionProvider" not in onnxruntime.get_available_providers():
                    logger.warning(
                        "CUDA provider not available for ONNX. Falling back to CPU."
                    )
                    self.provider = "cpu"
            except ImportError:
                logger.warning("ONNX Runtime not installed. Falling back to CPU.")
                self.provider = "cpu"
        logger.info(f"Sherpa-Onnx-ASR: Using {self.provider} for inference")

        self.recognizer = self._create_recognizer()

    def _create_recognizer(self):
        if self.model_type == "transducer":
            recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=self.encoder,
                decoder=self.decoder,
                joiner=self.joiner,
                tokens=self.tokens,
                num_threads=self.num_threads,
                sample_rate=self.SAMPLE_RATE,
                feature_dim=self.feature_dim,
                decoding_method=self.decoding_method,
                hotwords_file=self.hotwords_file,
                hotwords_score=self.hotwords_score,
                modeling_unit=self.modeling_unit,
                bpe_vocab=self.bpe_vocab,
                blank_penalty=self.blank_penalty,
                debug=self.debug,
                provider=self.provider,
            )
        elif self.model_type == "paraformer":
            recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
                paraformer=self.paraformer,
                tokens=self.tokens,
                num_threads=self.num_threads,
                sample_rate=self.SAMPLE_RATE,
                feature_dim=self.feature_dim,
                decoding_method=self.decoding_method,
                debug=self.debug,
                provider=self.provider,
            )
        elif self.model_type == "nemo_ctc":
            recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
                model=self.nemo_ctc,
                tokens=self.tokens,
                num_threads=self.num_threads,
                sample_rate=self.SAMPLE_RATE,
                feature_dim=self.feature_dim,
                decoding_method=self.decoding_method,
                debug=self.debug,
                provider=self.provider,
            )
        elif self.model_type == "wenet_ctc":
            recognizer = sherpa_onnx.OfflineRecognizer.from_wenet_ctc(
                model=self.wenet_ctc,
                tokens=self.tokens,
                num_threads=self.num_threads,
                sample_rate=self.SAMPLE_RATE,
                feature_dim=self.feature_dim,
                decoding_method=self.decoding_method,
                debug=self.debug,
                provider=self.provider,
            )
        elif self.model_type == "whisper":
            recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=self.whisper_encoder,
                decoder=self.whisper_decoder,
                tokens=self.tokens,
                num_threads=self.num_threads,
                decoding_method=self.decoding_method,
                debug=self.debug,
                language=self.whisper_language,
                task=self.whisper_task,
                tail_paddings=self.whisper_tail_paddings,
                provider=self.provider,
            )
        elif self.model_type == "tdnn_ctc":
            recognizer = sherpa_onnx.OfflineRecognizer.from_tdnn_ctc(
                model=self.tdnn_model,
                tokens=self.tokens,
                sample_rate=self.SAMPLE_RATE,
                feature_dim=self.feature_dim,
                num_threads=self.num_threads,
                decoding_method=self.decoding_method,
                debug=self.debug,
                provider=self.provider,
            )
        elif self.model_type == "sense_voice":
            if not self.sense_voice or not os.path.isfile(self.sense_voice):
                if self.sense_voice.startswith(
                    "./models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
                ):
                    logger.warning(
                        "SenseVoice model not found. Downloading the model..."
                    )

                    url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2"
                    output_dir = "./models"
                    # check the local file first before download
                    local_result = check_and_extract_local_file(url, output_dir)

                    if local_result is None:
                        logger.info("Local file not found. Downloading...")
                        download_and_extract(url, output_dir)
                    else:
                        logger.info("Local file found. Using existing file.")
                    # download_and_extract(
                    #     url="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2",
                    #     output_dir="./models",
                    # )
                else:
                    logger.critical(
                        "The SenseVoice model is missing. Please provide the path to the model.onnx file."
                    )
            recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=self.sense_voice,
                tokens=self.tokens,
                num_threads=self.num_threads,
                use_itn=self.use_itn,
                debug=self.debug,
                provider=self.provider,
            )
        else:
            raise ValueError(f"Invalid model type: {self.model_type}")

        return recognizer

    def transcribe_np(self, audio: np.ndarray) -> str:
        stream = self.recognizer.create_stream()
        stream.accept_waveform(self.SAMPLE_RATE, audio)
        self.recognizer.decode_streams([stream])
        return stream.result.text
