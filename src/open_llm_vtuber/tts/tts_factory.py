from typing import Callable, Dict
from .tts_interface import TTSInterface

_TTS_REGISTRY: Dict[str, Callable[..., TTSInterface]] = {}


def _register(engine_type: str) -> Callable:
    def decorator(fn: Callable[..., TTSInterface]) -> Callable[..., TTSInterface]:
        _TTS_REGISTRY[engine_type] = fn
        return fn
    return decorator


@_register("azure_tts")
def _create_azure_tts(**kwargs) -> TTSInterface:
    from .azure_tts import TTSEngine
    return TTSEngine(
        kwargs.get("api_key"),
        kwargs.get("region"),
        kwargs.get("voice"),
        kwargs.get("pitch"),
        kwargs.get("rate"),
    )


@_register("bark_tts")
def _create_bark_tts(**kwargs) -> TTSInterface:
    from .bark_tts import TTSEngine
    return TTSEngine(kwargs.get("voice"))


@_register("edge_tts")
def _create_edge_tts(**kwargs) -> TTSInterface:
    from .edge_tts import TTSEngine
    return TTSEngine(kwargs.get("voice"))


@_register("pyttsx3_tts")
def _create_pyttsx3_tts(**kwargs) -> TTSInterface:
    from .pyttsx3_tts import TTSEngine
    return TTSEngine()


@_register("cosyvoice_tts")
def _create_cosyvoice_tts(**kwargs) -> TTSInterface:
    from .cosyvoice_tts import TTSEngine
    return TTSEngine(
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


@_register("cosyvoice2_tts")
def _create_cosyvoice2_tts(**kwargs) -> TTSInterface:
    from .cosyvoice2_tts import TTSEngine
    return TTSEngine(
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


@_register("melo_tts")
def _create_melo_tts(**kwargs) -> TTSInterface:
    from .melo_tts import TTSEngine
    return TTSEngine(
        speaker=kwargs.get("speaker"),
        language=kwargs.get("language"),
        device=kwargs.get("device"),
        speed=kwargs.get("speed"),
    )


@_register("x_tts")
def _create_x_tts(**kwargs) -> TTSInterface:
    from .x_tts import TTSEngine
    return TTSEngine(
        api_url=kwargs.get("api_url"),
        speaker_wav=kwargs.get("speaker_wav"),
        language=kwargs.get("language"),
    )


@_register("gpt_sovits_tts")
def _create_gpt_sovits_tts(**kwargs) -> TTSInterface:
    from .gpt_sovits_tts import TTSEngine
    return TTSEngine(
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


@_register("siliconflow_tts")
def _create_siliconflow_tts(**kwargs) -> TTSInterface:
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


@_register("coqui_tts")
def _create_coqui_tts(**kwargs) -> TTSInterface:
    from .coqui_tts import TTSEngine
    return TTSEngine(
        model_name=kwargs.get("model_name"),
        speaker_wav=kwargs.get("speaker_wav"),
        language=kwargs.get("language"),
        device=kwargs.get("device"),
    )


@_register("fish_api_tts")
def _create_fish_api_tts(**kwargs) -> TTSInterface:
    from .fish_api_tts import TTSEngine
    return TTSEngine(
        api_key=kwargs.get("api_key"),
        reference_id=kwargs.get("reference_id"),
        latency=kwargs.get("latency"),
        base_url=kwargs.get("base_url"),
    )


@_register("minimax_tts")
def _create_minimax_tts(**kwargs) -> TTSInterface:
    from .minimax_tts import TTSEngine
    return TTSEngine(
        group_id=kwargs.get("group_id"),
        api_key=kwargs.get("api_key"),
        model=kwargs.get("model", "speech-02-turbo"),
        voice_id=kwargs.get("voice_id", "male-qn-qingse"),
        pronunciation_dict=kwargs.get("pronunciation_dict", ""),
    )


@_register("sherpa_onnx_tts")
def _create_sherpa_onnx_tts(**kwargs) -> TTSInterface:
    from .sherpa_onnx_tts import TTSEngine
    return TTSEngine(**kwargs)


@_register("openai_tts")
def _create_openai_tts(**kwargs) -> TTSInterface:
    from .openai_tts import TTSEngine
    return TTSEngine(
        model=kwargs.get("model"),
        voice=kwargs.get("voice"),
        api_key=kwargs.get("api_key"),
        base_url=kwargs.get("base_url"),
        file_extension=kwargs.get("file_extension"),
    )


@_register("spark_tts")
def _create_spark_tts(**kwargs) -> TTSInterface:
    from .spark_tts import TTSEngine
    return TTSEngine(
        api_url=kwargs.get("api_url"),
        prompt_wav_upload=kwargs.get("prompt_wav_upload"),
        api_name=kwargs.get("api_name"),
        gender=kwargs.get("gender"),
        pitch=kwargs.get("pitch"),
        speed=kwargs.get("speed"),
    )


@_register("elevenlabs_tts")
def _create_elevenlabs_tts(**kwargs) -> TTSInterface:
    from .elevenlabs_tts import TTSEngine
    return TTSEngine(
        api_key=kwargs.get("api_key"),
        voice_id=kwargs.get("voice_id"),
        model_id=kwargs.get("model_id", "eleven_multilingual_v2"),
        output_format=kwargs.get("output_format", "mp3_44100_128"),
        stability=kwargs.get("stability", 0.5),
        similarity_boost=kwargs.get("similarity_boost", 0.5),
        style=kwargs.get("style", 0.0),
        use_speaker_boost=kwargs.get("use_speaker_boost", True),
    )


@_register("cartesia_tts")
def _create_cartesia_tts(**kwargs) -> TTSInterface:
    from .cartesia_tts import TTSEngine
    return TTSEngine(
        api_key=kwargs.get("api_key"),
        voice_id=kwargs.get("voice_id", "6ccbfb76-1fc6-48f7-b71d-91ac6298247b"),
        model_id=kwargs.get("model_id", "sonic-3"),
        output_format=kwargs.get("output_format", "wav"),
        language=kwargs.get("language", "en"),
        emotion=kwargs.get("emotion", "neutral"),
        volume=kwargs.get("volume", 1.0),
        speed=kwargs.get("speed", 1.0),
    )


@_register("piper_tts")
def _create_piper_tts(**kwargs) -> TTSInterface:
    from .piper_tts import TTSEngine
    return TTSEngine(
        model_path=kwargs.get("model_path"),
        speaker_id=kwargs.get("speaker_id"),
        length_scale=kwargs.get("length_scale"),
        noise_scale=kwargs.get("noise_scale"),
        noise_w=kwargs.get("noise_w"),
        volume=kwargs.get("volume"),
        normalize_audio=kwargs.get("normalize_audio"),
        use_cuda=kwargs.get("use_cuda"),
    )


class TTSFactory:
    """Registry-based TTS engine factory."""

    @staticmethod
    def get_tts_engine(engine_type: str, **kwargs) -> TTSInterface:
        if engine_type in _TTS_REGISTRY:
            return _TTS_REGISTRY[engine_type](**kwargs)
        raise ValueError(f"Unknown TTS engine type: {engine_type}")

    @staticmethod
    def list_engines() -> list:
        return sorted(_TTS_REGISTRY.keys())

    @staticmethod
    def register(engine_type: str, factory: Callable[..., TTSInterface]) -> None:
        _TTS_REGISTRY[engine_type] = factory

    @staticmethod
    def unregister(engine_type: str) -> None:
        _TTS_REGISTRY.pop(engine_type, None)
