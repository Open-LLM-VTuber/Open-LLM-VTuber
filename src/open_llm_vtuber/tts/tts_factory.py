from typing import Type
from .tts_interface import TTSInterface


class TTSFactory:
    @staticmethod
    def get_tts_engine(engine_type, **kwargs) -> Type[TTSInterface]:
        if engine_type == "azure_tts":
            from .azure_tts import TTSEngine as AzureTTSEngine

            return AzureTTSEngine(
                kwargs.get("api_key"),
                kwargs.get("region"),
                kwargs.get("voice"),
                kwargs.get("pitch"),
                kwargs.get("rate"),
            )
        elif engine_type == "bark_tts":
            from .bark_tts import TTSEngine as BarkTTSEngine

            return BarkTTSEngine(kwargs.get("voice"))
        elif engine_type == "edge_tts":
            from .edge_tts import TTSEngine as EdgeTTSEngine

            return EdgeTTSEngine(kwargs.get("voice"))
        elif engine_type == "pyttsx3_tts":
            from .pyttsx3_tts import TTSEngine as Pyttsx3TTSEngine

            return Pyttsx3TTSEngine()
        elif engine_type == "cosyvoice_tts":
            from .cosyvoice_tts import TTSEngine as CosyvoiceTTSEngine

            return CosyvoiceTTSEngine(
                client_url=kwargs.get("client_url"),
                mode_checkbox_group=kwargs.get("mode_checkbox_group"),
                sft_dropdown=kwargs.get("sft_dropdown"),
                prompt_text=kwargs.get("prompt_text"),
                prompt_wav_upload_url=kwargs.get("prompt_wav_upload_url"),
                prompt_wav_record_url=kwargs.get("prompt_wav_record_url"),
                instruct_text=kwargs.get("instruct_text"),
                seed=kwargs.get("seed"),
                api_name=kwargs.get("api_name"),
            )
        elif engine_type == "cosyvoice2_tts":
            from .cosyvoice2_tts import TTSEngine as Cosyvoice2TTSEngine

            return Cosyvoice2TTSEngine(
                client_url=kwargs.get("client_url"),
                mode_checkbox_group=kwargs.get("mode_checkbox_group"),
                sft_dropdown=kwargs.get("sft_dropdown"),
                prompt_text=kwargs.get("prompt_text"),
                prompt_wav_upload_url=kwargs.get("prompt_wav_upload_url"),
                prompt_wav_record_url=kwargs.get("prompt_wav_record_url"),
                instruct_text=kwargs.get("instruct_text"),
                stream=kwargs.get("stream"),
                seed=kwargs.get("seed"),
                speed=kwargs.get("speed"),
                api_name=kwargs.get("api_name"),
            )
        elif engine_type == "melo_tts":
            from .melo_tts import TTSEngine as MeloTTSEngine

            return MeloTTSEngine(
                speaker=kwargs.get("speaker"),
                language=kwargs.get("language"),
                device=kwargs.get("device"),
                speed=kwargs.get("speed"),
            )
        elif engine_type == "x_tts":
            from .x_tts import TTSEngine as XTTSEngine

            return XTTSEngine(
                api_url=kwargs.get("api_url"),
                speaker_wav=kwargs.get("speaker_wav"),
                language=kwargs.get("language"),
            )
        elif engine_type == "gpt_sovits_tts":
            from .gpt_sovits_tts import TTSEngine as GSVEngine

            return GSVEngine(
                api_url=kwargs.get("api_url"),
                text_lang=kwargs.get("text_lang"),
                ref_audio_path=kwargs.get("ref_audio_path"),
                prompt_lang=kwargs.get("prompt_lang"),
                prompt_text=kwargs.get("prompt_text"),
                text_split_method=kwargs.get("text_split_method"),
                batch_size=kwargs.get("batch_size"),
                media_type=kwargs.get("media_type"),
                streaming_mode=kwargs.get("streaming_mode"),
            )
        elif engine_type == "siliconflow_tts":
            from .siliconflow_tts import SiliconFlowTTS

            return SiliconFlowTTS(
                api_url=kwargs.get("api_url"),
                api_key=kwargs.get("api_key"),
                default_model=kwargs.get("default_model"),
                default_voice=kwargs.get("default_voice"),
                sample_rate=kwargs.get("sample_rate"),
                response_format=kwargs.get("response_format"),
                stream=kwargs.get("stream"),
                speed=kwargs.get("speed"),
                gain=kwargs.get("gain"),
            )
        elif engine_type == "coqui_tts":
            from .coqui_tts import TTSEngine as CoquiTTSEngine

            return CoquiTTSEngine(
                model_name=kwargs.get("model_name"),
                speaker_wav=kwargs.get("speaker_wav"),
                language=kwargs.get("language"),
                device=kwargs.get("device"),
            )

        elif engine_type == "fish_api_tts":
            from .fish_api_tts import TTSEngine as FishAPITTSEngine

            return FishAPITTSEngine(
                api_key=kwargs.get("api_key"),
                reference_id=kwargs.get("reference_id"),
                latency=kwargs.get("latency"),
                base_url=kwargs.get("base_url"),
            )
        elif engine_type == "minimax_tts":
            from .minimax_tts import TTSEngine as MinimaxTTSEngine

            return MinimaxTTSEngine(
                group_id=kwargs.get("group_id"),
                api_key=kwargs.get("api_key"),
                model=kwargs.get("model", "speech-02-turbo"),
                voice_id=kwargs.get("voice_id", "male-qn-qingse"),
                pronunciation_dict=kwargs.get("pronunciation_dict", ""),
            )
        elif engine_type == "sherpa_onnx_tts":
            from .sherpa_onnx_tts import TTSEngine as SherpaOnnxTTSEngine

            return SherpaOnnxTTSEngine(**kwargs)
        elif engine_type == "openai_tts":
            from .openai_tts import TTSEngine as OpenAITTSEngine

            # Pass relevant config options, allowing defaults in openai_tts.py if not provided
            return OpenAITTSEngine(
                model=kwargs.get("model"),  # Will use default "kokoro" if not in kwargs
                voice=kwargs.get(
                    "voice"
                ),  # Will use default "af_sky+af_bella" if not in kwargs
                api_key=kwargs.get(
                    "api_key"
                ),  # Will use default "not-needed" if not in kwargs
                base_url=kwargs.get(
                    "base_url"
                ),  # Will use default "http://localhost:8880/v1" if not in kwargs
                file_extension=kwargs.get(
                    "file_extension"
                ),  # Will use default "mp3" if not in kwargs
            )

        elif engine_type == "spark_tts":
            #         api_url: str = "http://127.0.0.1:7860/",
            #         prompt_wav_upload: str = "voice_clone/voice_clone_voice.wav",
            #         api_name:str = "voice_clone",
            #         gender: str = "male",
            #         pitch: int = 3,
            #         speed: int = 3
            from .spark_tts import TTSEngine as SparkTTSEngine

            return SparkTTSEngine(
                api_url=kwargs.get("api_url"),
                prompt_wav_upload=kwargs.get("prompt_wav_upload"),
                api_name=kwargs.get("api_name"),
                gender=kwargs.get("gender"),
                pitch=kwargs.get("pitch"),
                speed=kwargs.get("speed"),
            )
        elif engine_type == "elevenlabs_tts":
            from .elevenlabs_tts import TTSEngine as ElevenLabsTTSEngine

            return ElevenLabsTTSEngine(
                api_key=kwargs.get("api_key"),
                voice_id=kwargs.get("voice_id"),
                model_id=kwargs.get("model_id", "eleven_multilingual_v2"),
                output_format=kwargs.get("output_format", "mp3_44100_128"),
                stability=kwargs.get("stability", 0.5),
                similarity_boost=kwargs.get("similarity_boost", 0.5),
                style=kwargs.get("style", 0.0),
                use_speaker_boost=kwargs.get("use_speaker_boost", True),
            )
        else:
            raise ValueError(f"Unknown TTS engine type: {engine_type}")


# Example usage:
# tts_engine = TTSFactory.get_tts_engine("azure", api_key="your_api_key", region="your_region", voice="your_voice")
# tts_engine.speak("Hello world")
if __name__ == "__main__":
    tts_engine = TTSFactory.get_tts_engine(
        "spark_tts",
        api_url="http://127.0.0.1:7860/voice_clone",
        used_voices=r"D:\python\spark_tts\收集的语音\纳西妲-完整.mp3",
    )
    tts_engine.generate_audio("Hello world")
