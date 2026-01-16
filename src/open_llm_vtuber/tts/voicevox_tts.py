import os
import httpx
from loguru import logger
from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    def __init__(
        self,
        client_url: str = "http://127.0.0.1:50021",
        voicevox_speaker_id: int = 8,
        pitch: float = 0.0,
        speed: float = 1.0,
        intonation: float = 1.0,
        volume: float = 1.0,
    ):
        """
        Initialize Voicevox TTS engine.
        
        Args:
            client_url: URL of the Voicevox server
            voicevox_speaker_id: Speaker ID
            pitch: Pitch adjustment (-0.15 to 0.15)
            speed: Speed adjustment (0.5 to 2.0)
            intonation: Intonation adjustment (0.0 to 2.0)
            volume: Volume adjustment (0.0 to 2.0)
        """
        self.client_url = client_url
        self.voicevox_speaker_id = voicevox_speaker_id
        self.pitch = pitch
        self.speed = speed
        self.intonation = intonation
        self.volume = volume
        
        self.file_extension = "wav"
        self.new_audio_dir = "cache"
        
        if not os.path.exists(self.new_audio_dir):
            os.makedirs(self.new_audio_dir)
    
    def generate_audio(self, text: str, file_name_no_ext=None) -> str:
        """
        Generate speech audio file using Voicevox TTS.
        
        Args:
            text: The text to speak
            file_name_no_ext: Name of the file without extension
        
        Returns:
            str: The path to the generated audio file
        """
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)
        
        try:
            # First, get the audio query
            query_url = f"{self.client_url}/audio_query"
            query_params = {
                "text": text,
                "speaker": self.voicevox_speaker_id,
            }
            
            with httpx.Client() as client:
                # Get audio query
                response = client.post(query_url, params=query_params)
                response.raise_for_status()
                audio_query = response.json()
            
            # Adjust parameters
            audio_query["speedScale"] = self.speed
            audio_query["pitchScale"] = self.pitch
            audio_query["intonationScale"] = self.intonation
            audio_query["volumeScale"] = self.volume
            
            # Generate audio
            synthesis_url = f"{self.client_url}/synthesis"
            synthesis_params = {
                "speaker": self.voicevox_speaker_id,
            }
            
            with httpx.Client() as client:
                response = client.post(
                    synthesis_url,
                    params=synthesis_params,
                    json=audio_query,
                )
                response.raise_for_status()
                
                # Save audio file
                with open(file_name, "wb") as f:
                    f.write(response.content)
            
            logger.info(f"Generated audio file: {file_name}")
            return file_name
            
        except Exception as e:
            logger.error(f"Error generating audio with Voicevox: {e}")
            return None
