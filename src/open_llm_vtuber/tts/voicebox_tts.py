import requests
from loguru import logger
from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    """
    VOICEBOX TTS Engine implementation.
    
    VOICEBOX is a Japanese text-to-speech software that runs locally.
    Default API endpoint: http://localhost:50021
    
    Speaker IDs (default):
    - 0: 四国めたん (あまあま)
    - 1: ずんだもん (あまあま)
    - 2: 四国めたん (ノーマル)
    - 3: ずんだもん (ノーマル)
    - 4: 四国めたん (セクシー)
    - 5: ずんだもん (セクシー)
    - 6: 四国めたん (ツンツン)
    - 7: ずんだもん (ツンツン)
    - 8: 春日部つむぎ (ノーマル)
    - 9: 波音リツ (ノーマル)
    - 10: 雨晴はう (ノーマル)
    - 11: 玄野武宏 (ノーマル)
    - 12: 白上虎太郎 (ふつう)
    - 13: 青山龍星 (ノーマル)
    - 14: 冥鳴ひまり (ノーマル)
    - 15: 九州そら (あまあま)
    - 16: 九州そら (ノーマル)
    - 17: 九州そら (セクシー)
    - 18: 九州そら (ツンツン)
    - 19: 九州そら (ささやき)
    - 20: もち子さん (ノーマル)
    - 21: 剣崎雌雄 (ノーマル)
    """
    
    def __init__(
        self,
        api_url: str = "http://localhost:50021",
        speaker_id: int = 1,  # Default: ずんだもん (あまあま)
        speed_scale: float = 1.0,
        pitch_scale: float = 0.0,
        intonation_scale: float = 1.0,
        volume_scale: float = 1.0,
        pre_phoneme_length: float = 0.1,
        post_phoneme_length: float = 0.1,
    ):
        """
        Initialize VOICEBOX TTS Engine.
        
        Args:
            api_url: VOICEBOX API endpoint URL
            speaker_id: Speaker ID (see class docstring for available speakers)
            speed_scale: Speech speed (0.5-2.0, default: 1.0)
            pitch_scale: Pitch adjustment (-0.15-0.15, default: 0.0)
            intonation_scale: Intonation strength (0.0-2.0, default: 1.0)
            volume_scale: Volume (0.0-2.0, default: 1.0)
            pre_phoneme_length: Silence before speech (0.0-1.5, default: 0.1)
            post_phoneme_length: Silence after speech (0.0-1.5, default: 0.1)
        """
        self.api_url = api_url.rstrip('/')
        self.speaker_id = speaker_id
        self.speed_scale = speed_scale
        self.pitch_scale = pitch_scale
        self.intonation_scale = intonation_scale
        self.volume_scale = volume_scale
        self.pre_phoneme_length = pre_phoneme_length
        self.post_phoneme_length = post_phoneme_length
        self.file_extension = "wav"
        
        # Check if VOICEBOX is running
        self._check_connection()
    
    def _check_connection(self):
        """Check if VOICEBOX API is accessible."""
        try:
            response = requests.get(f"{self.api_url}/version", timeout=5)
            response.raise_for_status()
            version = response.json()
            logger.info(f"Connected to VOICEBOX version: {version}")
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Failed to connect to VOICEBOX at {self.api_url}. "
                f"Make sure VOICEBOX is running. Error: {e}"
            )
    
    def get_speakers(self):
        """Get available speakers from VOICEBOX."""
        try:
            response = requests.get(f"{self.api_url}/speakers", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get speakers: {e}")
            return []
    
    def generate_audio(self, text, file_name_no_ext=None):
        """
        Generate audio using VOICEBOX API.
        
        Args:
            text: Text to synthesize
            file_name_no_ext: Optional filename without extension
            
        Returns:
            Path to generated audio file or None if failed
        """
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)
        
        try:
            # Step 1: Create audio query
            logger.debug(f"Creating audio query for text: {text[:50]}...")
            query_response = requests.post(
                f"{self.api_url}/audio_query",
                params={
                    "text": text,
                    "speaker": self.speaker_id
                },
                timeout=30
            )
            query_response.raise_for_status()
            query_data = query_response.json()
            
            # Step 2: Adjust parameters
            query_data["speedScale"] = self.speed_scale
            query_data["pitchScale"] = self.pitch_scale
            query_data["intonationScale"] = self.intonation_scale
            query_data["volumeScale"] = self.volume_scale
            query_data["prePhonemeLength"] = self.pre_phoneme_length
            query_data["postPhonemeLength"] = self.post_phoneme_length
            
            # Step 3: Synthesize audio
            logger.debug("Synthesizing audio...")
            synthesis_response = requests.post(
                f"{self.api_url}/synthesis",
                params={"speaker": self.speaker_id},
                json=query_data,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            synthesis_response.raise_for_status()
            
            # Step 4: Save audio file
            with open(file_name, "wb") as audio_file:
                audio_file.write(synthesis_response.content)
            
            logger.info(f"Generated VOICEBOX audio: {file_name}")
            return file_name
            
        except requests.exceptions.ConnectionError:
            logger.error(
                f"Cannot connect to VOICEBOX at {self.api_url}. "
                "Please make sure VOICEBOX is running."
            )
            return None
        except requests.exceptions.Timeout:
            logger.error("VOICEBOX request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"VOICEBOX API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in VOICEBOX TTS: {e}")
            return None