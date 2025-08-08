# Standard library imports
import os

# Third-party imports
from loguru import logger
from parler_tts import ParlerTTSForConditionalGeneration
import soundfile as sf
import torch
from transformers import AutoTokenizer

# Local imports
from .tts_interface import TTSInterface


class ParlerTTSEngine(TTSInterface):
    """Parler-TTS text-to-speech engine implementation.
    
    This class provides text-to-speech functionality using Parler-TTS models,
    which can generate speech with customizable voice descriptions.
    
    Attributes:
        device (str): The device to run the model on (e.g., 'cpu', 'cuda').
        voice_description (str): Description of the desired voice characteristics.
        model: The loaded Parler-TTS model.
        tokenizer: The tokenizer for processing text inputs.
        sampling_rate (int): The audio sampling rate from the model config.
    """
    
    def __init__(
        self,
        model_name: str = "parler-tts/parler-tts-mini-v1",
        device: str = "auto",
        voice_description: str = "A clear female voice, medium pitch and speed.",
    ):
        """Initialize the Parler-TTS engine.
        
        Args:
            model_name (str): The name/path of the Parler-TTS model to load.
                Defaults to "parler-tts/parler-tts-mini-v1".
            device (str): The device to run the model on. Use "auto" for 
                automatic device selection, or specify "cpu"/"cuda" explicitly.
                Defaults to "auto".
            voice_description (str): A text description of the desired voice
                characteristics (e.g., gender, pitch, speed). Defaults to
                "A clear female voice, medium pitch and speed.".
        """
        if device and device != "auto":
            self.device = device
        else:
            logger.info("Parler-TTS: Auto-detecting device")
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.voice_description = voice_description

        logger.info(f"Parler-TTS: Using device: {self.device}")
        logger.info(f"Parler-TTS: Loading model {model_name}")

        try:
            self.model = ParlerTTSForConditionalGeneration.from_pretrained(model_name).to(
                self.device
            )
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.sampling_rate = self.model.config.sampling_rate
            
            logger.info(f"Parler-TTS: Model loaded successfully (sampling rate: {self.sampling_rate}Hz)")
        except Exception as e:
            logger.error(f"Parler-TTS: Failed to load model {model_name}: {str(e)}")
            raise RuntimeError(f"Failed to initialize Parler-TTS model: {str(e)}")

    def generate_audio(self, text: str, file_name_no_ext: str | None = None) -> str:
        """Generate audio from text using Parler-TTS.
        
        Args:
            text (str): The text to convert to speech.
            file_name_no_ext (str | None): Optional base filename without extension
                for the output audio file. If None, a default name will be generated.
        
        Returns:
            str: The path to the generated audio file.
            
        Raises:
            RuntimeError: If audio generation fails for any reason.
            FileNotFoundError: If the output audio file is not created successfully.
        """
        output_path = self.generate_cache_file_name(file_name_no_ext, "wav")

        try:
            logger.debug(f"Parler-TTS: Generating audio for text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Tokenize voice description and text prompt
            desc_ids = self.tokenizer(
                self.voice_description, return_tensors="pt"
            ).input_ids.to(self.device)
            prompt_ids = self.tokenizer(text, return_tensors="pt").input_ids.to(
                self.device
            )

            # Generate audio
            generation = self.model.generate(
                input_ids=desc_ids, prompt_input_ids=prompt_ids
            )
            audio_arr = generation.cpu().numpy().squeeze()

            # Save audio file
            sf.write(output_path, audio_arr, self.sampling_rate)

            # Verify file was created
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Output audio file not created: {output_path}")

            logger.debug(f"Parler-TTS: Audio saved to {output_path}")
            return output_path

        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except Exception as e:
            logger.error(f"Parler-TTS: Audio generation failed: {str(e)}")
            raise RuntimeError(f"Failed to generate audio with Parler-TTS: {str(e)}")

