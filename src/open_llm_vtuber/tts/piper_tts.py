import os
import wave

from loguru import logger
from .tts_interface import TTSInterface

try:
    from piper import PiperVoice
    from piper.voice import SynthesisConfig

    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False
    logger.warning("piper-tts not installed. Run: uv add piper-tts")


# Piper TTS requires trained ONNX model files for speech synthesis
# Recommended models:
# zh_CN-huayan-medium
# en_US-lessac-medium
# ja_JP-natsuya-medium
# You can manually download Chinese models from: https://huggingface.co/csukuangfj/vits-piper-zh_CN-huayan-medium/tree/main
# Find other models at: https://huggingface.co/models or train your own
# Download both .onnx and .onnx.json files to models/piper/ directory


class TTSEngine(TTSInterface):
    def __init__(
        self,
        model_path: str = "models/piper/zh_CN-huayan-medium.onnx",
        speaker_id: int = 0,
        length_scale: float = 1.0,
        noise_scale: float = 0.667,
        noise_w: float = 0.8,
        volume: float = 1.0,
        normalize_audio: bool = True,
        use_cuda: bool = False,
    ):
        """Initializes the Piper TTS engine using the Python API.

        Args:
            model_path: Path to the Piper ONNX model file.
            speaker_id: Speaker ID for multi-speaker models.
            length_scale: Speed control (e.g., 1.0 is normal speed).
            noise_scale: Audio variation level (0.0-1.0).
            noise_w: Speaking style variation (0.0-1.0).
            volume: Volume level (0.0-1.0).
            normalize_audio: Whether to normalize audio.
            use_cuda: Whether to use GPU acceleration.
        """
        if not PIPER_AVAILABLE:
            raise ImportError(
                "piper-tts is required. Install with: pip install piper-tts"
            )

        self.model_path = model_path
        self.speaker_id = speaker_id
        self.length_scale = length_scale
        self.noise_scale = noise_scale
        self.noise_w = noise_w
        self.volume = volume
        self.normalize_audio = normalize_audio
        self.use_cuda = use_cuda

        # Check if model file exists
        if not os.path.exists(self.model_path):
            logger.warning(f"Piper model not found at: {self.model_path}")
            logger.warning(
                "Download a model with: python3 -m piper.download_voices zh_CN-huayan-medium"
            )
            logger.warning("Or download from: https://huggingface.co/models")
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        # Load Piper voice model
        try:
            logger.info(f"Loading Piper model: {self.model_path}")
            self.voice = PiperVoice.load(self.model_path, use_cuda=self.use_cuda)
            logger.info("Piper model loaded successfully")
        except Exception as e:
            logger.critical(f"Failed to load Piper model: {e}")
            raise

        # Create synthesis configuration
        self.syn_config = SynthesisConfig(
            volume=self.volume,
            length_scale=self.length_scale,
            noise_scale=self.noise_scale,
            noise_w_scale=self.noise_w,
            normalize_audio=self.normalize_audio,
            speaker_id=self.speaker_id,
        )

    def generate_audio(
        self, text: str, file_name_no_ext: str | None = None
    ) -> str | None:
        """Generates a speech audio file using the Piper TTS Python API.

        Args:
            text: The text to convert to speech.
            file_name_no_ext: The name of the file without the extension. Defaults to None.

        Returns:
            The path to the generated audio file, or None on failure.
        """
        file_name = self.generate_cache_file_name(file_name_no_ext)

        try:
            # Generate audio using PiperVoice.synthesize_wav
            with wave.open(file_name, "wb") as wav_file:
                self.voice.synthesize_wav(text, wav_file, syn_config=self.syn_config)

            logger.info(f"Generated audio file: {file_name}")
            return file_name

        except Exception as e:
            logger.critical(f"Error: Piper TTS unable to generate audio: {e}")
            return None
