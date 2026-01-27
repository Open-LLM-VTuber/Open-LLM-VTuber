from gradio_client import Client, file
from loguru import logger
from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    def __init__(
        self,
        client_url="http://127.0.0.1:50000/",
        mode_checkbox_group="预训练音色",
        sft_dropdown="中文女",
        prompt_text="",
        prompt_wav_upload_url="https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav",
        prompt_wav_record_url="https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav",
        instruct_text="",
        seed=0,
        api_name="/generate_audio",
    ):
        self.client = Client(client_url)

        self.mode_checkbox_group = mode_checkbox_group
        self.sft_dropdown = sft_dropdown
        self.prompt_text = prompt_text
        self.prompt_wav_upload = file(prompt_wav_upload_url)
        self.prompt_wav_record = file(prompt_wav_record_url)
        self.instruct_text = instruct_text
        self.seed = seed
        self.api_name = api_name

    def generate_audio(self, text, file_name_no_ext=None):
        if file_name_no_ext is not None:
            logger.warning(
                "Warning: customizing the temp file name with file_name_no_ext is not supported by cosyvoiceTTS and will be ignored."
            )

        result_wav_path = self.client.predict(
            tts_text=text,
            mode_checkbox_group=self.mode_checkbox_group,
            sft_dropdown=self.sft_dropdown,
            prompt_text=self.prompt_text,
            prompt_wav_upload=self.prompt_wav_upload,
            prompt_wav_record=self.prompt_wav_record,
            instruct_text=self.instruct_text,
            seed=self.seed,
            api_name=self.api_name,
        )

        return result_wav_path
