import sys
import os

import sherpa_onnx
import soundfile as sf
from loguru import logger
from .tts_interface import TTSInterface

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)


class TTSEngine(TTSInterface):
    def __init__(
        self,
        vits_model: str,
        model_type = "vits",
        voices="",
        vits_lexicon="",
        vits_tokens="",
        vits_data_dir="",
        vits_dict_dir="",
        tts_rule_fsts="",
        max_num_sentences=2,
        sid=0,
        provider="cpu",
        num_threads=1,
        speed=1.0,
        debug=False,
    ):
        self.model = vits_model
        self.model_type = model_type.lower()
        self.voices = voices
        self.lexicon = vits_lexicon
        self.tokens = vits_tokens
        self.data_dir = vits_data_dir
        self.dict_dir = vits_dict_dir
        self.tts_rule_fsts = tts_rule_fsts
        self.max_num_sentences = max_num_sentences
        self.sid = sid  # Speaker ID
        self.provider = provider  # Computation provider (e.g., "cpu", "cuda")
        self.num_threads = num_threads
        self.speed = speed  # Speech speed
        self.debug = debug  # Debug mode flag

        self.file_extension = "wav"
        self.new_audio_dir = "cache"

        if not os.path.exists(self.new_audio_dir):
            os.makedirs(self.new_audio_dir)

        self.tts = self.initialize_tts()

    def initialize_tts(self):
        """
        Initialize the sherpa-onnx TTS engine.
        """

        model_config_map = {
            'vits': sherpa_onnx.OfflineTtsVitsModelConfig,
            'matcha': sherpa_onnx.OfflineTtsMatchaModelConfig,
            'kokoro': sherpa_onnx.OfflineTtsKokoroModelConfig,
            'kitten': sherpa_onnx.OfflineTtsKittenModelConfig,
        }
        config_class = model_config_map.get(self.model_type)

        if config_class:
            params = {
                'model': self.model,
                'lexicon': self.lexicon,
                'data_dir': self.data_dir,
                'dict_dir': self.dict_dir,
                'tokens': self.tokens,
            }

            if self.model_type == 'kokoro' or self.model_type == 'kitten':
                params['voices'] = self.voices

            # ... create params dict and instantiate
            model_config_obj = config_class(**params)
            model = sherpa_onnx.OfflineTtsModelConfig(
                **{self.model_type: model_config_obj},

                provider=self.provider,
                debug=self.debug,
                num_threads=self.num_threads,
            )

        # Construct the configuration for the TTS engine
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=model,
            rule_fsts=self.tts_rule_fsts,
            max_num_sentences=self.max_num_sentences,
        )

        # Validate the configuration
        if not tts_config.validate():
            raise ValueError("Please check your sherpa-onnx TTS config")

        # Create and return the sherpa-onnx OfflineTts object
        return sherpa_onnx.OfflineTts(tts_config)

    def generate_audio(self, text, file_name_no_ext=None):
        """
        Generate speech audio file using sherpa-onnx TTS.

        Parameters:
            text (str): The text to speak.
            file_name_no_ext (str, optional): Name of the file without extension.

        Returns:
            str: The path to the generated audio file.
        """
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)

        try:
            audio = self.tts.generate(text, sid=self.sid, speed=self.speed)

            if len(audio.samples) == 0:
                logger.error(
                    "Error in generating audios. Please read previous error messages."
                )
                return None

            sf.write(
                file_name,
                audio.samples,
                samplerate=audio.sample_rate,
                subtype="PCM_16",
            )

            return file_name

        except Exception as e:
            logger.critical(f"\nError: sherpa-onnx unable to generate audio: {e}")
            return None
