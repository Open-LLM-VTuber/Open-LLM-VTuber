import sys
import os
import azure.cognitiveservices.speech as speechsdk
from loguru import logger
from .tts_interface import TTSInterface

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)


class TTSEngine(TTSInterface):
    temp_audio_file = "temp"
    file_extension = "wav"
    new_audio_dir = "cache"

    def __init__(self, api_key, region, voice, pitch=0, rate=1.0):
        """
        Initialize the Azure Text-to-Speech service
        api_key: str
            the Azure API key. Default is the value in api_keys.py
        region: str
            the Azure region. Default is the value in api_keys.py
        voice: str
            the voice to use. Default is the value in api_keys.py
        pitch: int
            the pitch adjustment. (percentage, from -100 to 100) Default is 0 (no adjustment)
        rate: float
            the speaking rate. Default is 1.0 (normal speed)
        """
        # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
        self.speech_config = speechsdk.SpeechConfig(subscription=api_key, region=region)
        # The language of the voice that speaks.
        self.speech_config.speech_synthesis_voice_name = voice

        # Initialize pitch and rate
        self.pitch = pitch
        self.rate = rate

        if not os.path.exists(self.new_audio_dir):
            os.makedirs(self.new_audio_dir)

        self.speaker_audio_config = speechsdk.audio.AudioOutputConfig(
            use_default_speaker=True
        )

    def generate_audio(self, text, file_name_no_ext=None):
        """
        Generate speech audio file using TTS.
        text: str
            the text to speak
        file_name_no_ext: str
            name of the file without extension

        Returns:
        str: the path to the generated audio file
        """

        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)

        file_audio_config = speechsdk.audio.AudioOutputConfig(filename=file_name)

        self.__speak_with_audio_config(text, audio_config=file_audio_config)
        return file_name

    def __speak_with_audio_config(
        self,
        text,
        audio_config,
        on_speak_start_callback=None,
        on_speak_end_callback=None,
    ):
        """
        speak the text with specified audio configuration
        text: str
            the text to speak
        audio_config: speechsdk.audio.AudioOutputConfig
            the audio configuration to use
        on_speak_start_callback: function
            the callback function to call when synthesis starts
        on_speak_end_callback: function
            the callback function to call when synthesis ends
        """
        speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config, audio_config=audio_config
        )

        # check if the text is empty or not a string
        if not isinstance(text, str):
            logger.warning("AzureTTS: The text cannot be non-string.")
            logger.warning(f"Received type: {type(text)} and value: {text}")
            return
        text = text.strip()

        if text.strip() == "":
            logger.warning("AzureTTS: There is no text to speak.")
            logger.info(f"Received text: {text}")
            return

        # Wrap the text with SSML to adjust pitch and rate
        ssml_text = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
            <voice name="{self.speech_config.speech_synthesis_voice_name}">
                <prosody pitch="{self.pitch}%" rate="{self.rate}">
                    {text}
                </prosody>
            </voice>
        </speak>
        """

        if on_speak_start_callback is not None:
            on_speak_start_callback()

        speech_synthesis_result = speech_synthesizer.speak_ssml(ssml_text)

        if on_speak_end_callback is not None:
            on_speak_end_callback()

        if (
            speech_synthesis_result.reason
            == speechsdk.ResultReason.SynthesizingAudioCompleted
        ):
            if on_speak_end_callback is not None:
                on_speak_end_callback()
            logger.info(f">> Speech synthesized for text [{text}]")
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            logger.info(f"Speech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    logger.error(f"Error details: {cancellation_details.error_details}")
                    logger.error(
                        "Did you set the speech resource key and region values?"
                    )


if __name__ == "__main__":
    tts = TTSEngine(
        api_key="test-api-key",
        region="eastus",
        voice="en-US-AshleyNeural",
        pitch=26,
        rate=1.0,
    )

    tts.generate_audio(
        "Hello, how are you? Hey! Tell me a story of a super intelligent person and a stupid AI fight together and eventuall killed each other",
        "hello",
    )

    # tts.speak("I am fine, thank you.")
    # tts.speak("Goodbye!")
