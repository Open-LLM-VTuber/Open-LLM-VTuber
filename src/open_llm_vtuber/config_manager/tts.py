# config_manager/tts.py
from pydantic import ValidationInfo, Field, model_validator
from typing import Literal, Optional, Dict, ClassVar
from .i18n import I18nMixin, Description


class AzureTTSConfig(I18nMixin):
    """Configuration for Azure TTS service."""

    api_key: str = Field(..., alias="api_key")
    region: str = Field(..., alias="region")
    voice: str = Field(..., alias="voice")
    pitch: str = Field(..., alias="pitch")
    rate: str = Field(..., alias="rate")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(
            en="API key for Azure TTS service", zh="Azure TTS 服务的 API 密钥"
        ),
        "region": Description(
            en="Azure region (e.g., eastus)", zh="Azure 区域（如 eastus）"
        ),
        "voice": Description(
            en="Voice name to use for Azure TTS", zh="Azure TTS 使用的语音名称"
        ),
        "pitch": Description(en="Pitch adjustment percentage", zh="音高调整百分比"),
        "rate": Description(en="Speaking rate adjustment", zh="语速调整"),
    }


class BarkTTSConfig(I18nMixin):
    """Configuration for Bark TTS."""

    voice: str = Field(..., alias="voice")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "voice": Description(
            en="Voice name to use for Bark TTS", zh="Bark TTS 使用的语音名称"
        ),
    }


class EdgeTTSConfig(I18nMixin):
    """Configuration for Edge TTS."""

    voice: str = Field(..., alias="voice")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "voice": Description(
            en="Voice name to use for Edge TTS (use 'edge-tts --list-voices' to list available voices)",
            zh="Edge TTS 使用的语音名称（使用 'edge-tts --list-voices' 列出可用语音）",
        ),
    }


class CosyvoiceTTSConfig(I18nMixin):
    """Configuration for Cosyvoice TTS."""

    client_url: str = Field(..., alias="client_url")
    mode_checkbox_group: str = Field(..., alias="mode_checkbox_group")
    sft_dropdown: str = Field(..., alias="sft_dropdown")
    prompt_text: str = Field(..., alias="prompt_text")
    prompt_wav_upload_url: str = Field(..., alias="prompt_wav_upload_url")
    prompt_wav_record_url: str = Field(..., alias="prompt_wav_record_url")
    instruct_text: str = Field(..., alias="instruct_text")
    seed: int = Field(..., alias="seed")
    api_name: str = Field(..., alias="api_name")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "client_url": Description(
            en="URL of the CosyVoice Gradio web UI", zh="CosyVoice Gradio Web UI 的 URL"
        ),
        "mode_checkbox_group": Description(
            en="Mode checkbox group value", zh="模式复选框组值"
        ),
        "sft_dropdown": Description(en="SFT dropdown value", zh="SFT 下拉框值"),
        "prompt_text": Description(en="Prompt text", zh="提示文本"),
        "prompt_wav_upload_url": Description(
            en="URL for prompt WAV file upload", zh="提示音频文件上传 URL"
        ),
        "prompt_wav_record_url": Description(
            en="URL for prompt WAV file recording", zh="提示音频文件录制 URL"
        ),
        "instruct_text": Description(en="Instruction text", zh="指令文本"),
        "seed": Description(en="Random seed", zh="随机种子"),
        "api_name": Description(en="API endpoint name", zh="API 端点名称"),
    }


class Cosyvoice2TTSConfig(I18nMixin):
    """Configuration for Cosyvoice2 TTS."""

    client_url: str = Field(..., alias="client_url")
    mode_checkbox_group: str = Field(..., alias="mode_checkbox_group")
    sft_dropdown: str = Field(..., alias="sft_dropdown")
    prompt_text: str = Field(..., alias="prompt_text")
    prompt_wav_upload_url: str = Field(..., alias="prompt_wav_upload_url")
    prompt_wav_record_url: str = Field(..., alias="prompt_wav_record_url")
    instruct_text: str = Field(..., alias="instruct_text")
    stream: bool = Field(..., alias="stream")
    seed: int = Field(..., alias="seed")
    speed: float = Field(..., alias="speed")
    api_name: str = Field(..., alias="api_name")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "client_url": Description(
            en="URL of the CosyVoice Gradio web UI", zh="CosyVoice Gradio Web UI 的 URL"
        ),
        "mode_checkbox_group": Description(
            en="Mode checkbox group value", zh="模式复选框组值"
        ),
        "sft_dropdown": Description(en="SFT dropdown value", zh="SFT 下拉框值"),
        "prompt_text": Description(en="Prompt text", zh="提示文本"),
        "prompt_wav_upload_url": Description(
            en="URL for prompt WAV file upload", zh="提示音频文件上传 URL"
        ),
        "prompt_wav_record_url": Description(
            en="URL for prompt WAV file recording", zh="提示音频文件录制 URL"
        ),
        "instruct_text": Description(en="Instruction text", zh="指令文本"),
        "stream": Description(en="Streaming inference", zh="流式推理"),
        "seed": Description(en="Random seed", zh="随机种子"),
        "speed": Description(en="Speech speed multiplier", zh="语速倍数"),
        "api_name": Description(en="API endpoint name", zh="API 端点名称"),
    }


class MeloTTSConfig(I18nMixin):
    """Configuration for Melo TTS."""

    speaker: str = Field(..., alias="speaker")
    language: str = Field(..., alias="language")
    device: str = Field("auto", alias="device")
    speed: float = Field(1.0, alias="speed")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "speaker": Description(
            en="Speaker name (e.g., EN-Default, ZH)",
            zh="说话人名称（如 EN-Default、ZH）",
        ),
        "language": Description(
            en="Language code (e.g., EN, ZH)", zh="语言代码（如 EN、ZH）"
        ),
        "device": Description(
            en="Device to use (auto, cpu, cuda, cuda:0, mps)",
            zh="使用的设备（auto、cpu、cuda、cuda:0、mps）",
        ),
        "speed": Description(en="Speech speed multiplier", zh="语速倍数"),
    }


class XTTSConfig(I18nMixin):
    """Configuration for XTTS."""

    api_url: str = Field(..., alias="api_url")
    speaker_wav: str = Field(..., alias="speaker_wav")
    language: str = Field(..., alias="language")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_url": Description(
            en="URL of the XTTS API endpoint", zh="XTTS API 端点的 URL"
        ),
        "speaker_wav": Description(
            en="Speaker reference WAV file", zh="说话人参考音频文件"
        ),
        "language": Description(
            en="Language code (e.g., en, zh)", zh="语言代码（如 en、zh）"
        ),
    }


class GPTSoVITSConfig(I18nMixin):
    """Configuration for GPT-SoVITS."""

    api_url: str = Field(..., alias="api_url")
    text_lang: str = Field(..., alias="text_lang")
    ref_audio_path: str = Field(..., alias="ref_audio_path")
    prompt_lang: str = Field(..., alias="prompt_lang")
    prompt_text: str = Field(..., alias="prompt_text")
    text_split_method: str = Field(..., alias="text_split_method")
    batch_size: str = Field(..., alias="batch_size")
    media_type: str = Field(..., alias="media_type")
    streaming_mode: str = Field(..., alias="streaming_mode")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_url": Description(
            en="URL of the GPT-SoVITS API endpoint", zh="GPT-SoVITS API 端点的 URL"
        ),
        "text_lang": Description(en="Language of the input text", zh="输入文本的语言"),
        "ref_audio_path": Description(
            en="Path to reference audio file", zh="参考音频文件路径"
        ),
        "prompt_lang": Description(en="Language of the prompt", zh="提示词语言"),
        "prompt_text": Description(en="Prompt text", zh="提示文本"),
        "text_split_method": Description(
            en="Method for splitting text", zh="文本分割方法"
        ),
        "batch_size": Description(en="Batch size for processing", zh="处理批次大小"),
        "media_type": Description(en="Output media type", zh="输出媒体类型"),
        "streaming_mode": Description(en="Enable streaming mode", zh="启用流式模式"),
    }


class FishAPITTSConfig(I18nMixin):
    """Configuration for Fish API TTS."""

    api_key: str = Field(..., alias="api_key")
    reference_id: str = Field(..., alias="reference_id")
    latency: Literal["normal", "balanced"] = Field(..., alias="latency")
    base_url: str = Field(..., alias="base_url")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(
            en="API key for Fish TTS service", zh="Fish TTS 服务的 API 密钥"
        ),
        "reference_id": Description(
            en="Voice reference ID from Fish Audio website",
            zh="来自 Fish Audio 网站的语音参考 ID",
        ),
        "latency": Description(
            en="Latency mode (normal or balanced)", zh="延迟模式（normal 或 balanced）"
        ),
        "base_url": Description(
            en="Base URL for Fish TTS API", zh="Fish TTS API 的基础 URL"
        ),
    }


class CoquiTTSConfig(I18nMixin):
    """Configuration for Coqui TTS."""

    model_name: str = Field(..., alias="model_name")
    speaker_wav: str = Field("", alias="speaker_wav")
    language: str = Field(..., alias="language")
    device: str = Field("", alias="device")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "model_name": Description(
            en="Name of the TTS model to use", zh="要使用的 TTS 模型名称"
        ),
        "speaker_wav": Description(
            en="Path to speaker WAV file for voice cloning",
            zh="用于声音克隆的说话人音频文件路径",
        ),
        "language": Description(
            en="Language code (e.g., en, zh)", zh="语言代码（如 en、zh）"
        ),
        "device": Description(
            en="Device to use (cuda, cpu, or empty for auto)",
            zh="使用的设备（cuda、cpu 或留空以自动选择）",
        ),
    }


class SherpaOnnxTTSConfig(I18nMixin):
    """Configuration for Sherpa Onnx TTS."""

    vits_model: str = Field(..., alias="vits_model")
    vits_lexicon: Optional[str] = Field(None, alias="vits_lexicon")
    vits_tokens: str = Field(..., alias="vits_tokens")
    vits_data_dir: Optional[str] = Field(None, alias="vits_data_dir")
    vits_dict_dir: Optional[str] = Field(None, alias="vits_dict_dir")
    tts_rule_fsts: Optional[str] = Field(None, alias="tts_rule_fsts")
    max_num_sentences: int = Field(2, alias="max_num_sentences")
    sid: int = Field(1, alias="sid")
    provider: Literal["cpu", "cuda", "coreml"] = Field("cpu", alias="provider")
    num_threads: int = Field(1, alias="num_threads")
    speed: float = Field(1.0, alias="speed")
    debug: bool = Field(False, alias="debug")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "vits_model": Description(en="Path to VITS model file", zh="VITS 模型文件路径"),
        "vits_lexicon": Description(
            en="Path to lexicon file (optional)", zh="词典文件路径（可选）"
        ),
        "vits_tokens": Description(en="Path to tokens file", zh="词元文件路径"),
        "vits_data_dir": Description(
            en="Path to espeak-ng data directory (optional)",
            zh="espeak-ng 数据目录路径（可选）",
        ),
        "vits_dict_dir": Description(
            en="Path to Jieba dictionary directory (optional)",
            zh="结巴词典目录路径（可选）",
        ),
        "tts_rule_fsts": Description(
            en="Path to rule FSTs file (optional)", zh="规则 FST 文件路径（可选）"
        ),
        "max_num_sentences": Description(
            en="Maximum number of sentences per batch", zh="每批次最大句子数"
        ),
        "sid": Description(
            en="Speaker ID for multi-speaker models", zh="多说话人模型的说话人 ID"
        ),
        "provider": Description(
            en="Computation provider (cpu, cuda, or coreml)",
            zh="计算提供者（cpu、cuda 或 coreml）",
        ),
        "num_threads": Description(en="Number of computation threads", zh="计算线程数"),
        "speed": Description(en="Speech speed multiplier", zh="语速倍数"),
        "debug": Description(en="Enable debug mode", zh="启用调试模式"),
    }


class SiliconFlowTTSConfig(I18nMixin):
    """Configuration for SiliconFlow TTS."""

    api_url: str = Field("https://api.siliconflow.cn/v1/audio/speech", alias="api_url")
    api_key: str = Field(..., alias="api_key")
    default_model: str = Field("FunAudioLLM/CosyVoice2-0.5B", alias="default_model")
    default_voice: str = Field(
        "speech:Dreamflowers:5bdstvc39i:xkqldnpasqmoqbakubom", alias="default_voice"
    )
    sample_rate: int = Field(32000, alias="sample_rate")
    response_format: str = Field("mp3", alias="response_format")
    stream: bool = Field(True, alias="stream")
    speed: float = Field(1, alias="speed")
    gain: int = Field(0, alias="gain")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(
            en="API key for SiliconFlow TTS service",
            zh="SiliconFlow TTS 服务的 API 密钥",
        ),
        "url": Description(
            en="API endpoint URL for SiliconFlow TTS",
            zh="SiliconFlow TTS 的 API 端点 URL",
        ),
        "model": Description(
            en="Model to use for SiliconFlow TTS", zh="SiliconFlow TTS 使用的模型"
        ),
        "voice": Description(
            en="Voice name to use for SiliconFlow TTS",
            zh="SiliconFlow TTS 使用的语音名称",
        ),
        "sample_rate": Description(
            en="Sample rate of the output audio", zh="输出音频的采样率"
        ),
        "stream": Description(en="Enable streaming mode", zh="启用流式模式"),
        "speed": Description(en="Speaking speed multiplier", zh="语速倍数"),
        "gain": Description(en="Audio gain adjustment", zh="音频增益调整"),
    }


class OpenAITTSConfig(I18nMixin):
    """Configuration for OpenAI-compatible TTS client."""

    model: Optional[str] = Field(None, alias="model")
    voice: Optional[str] = Field(None, alias="voice")
    api_key: Optional[str] = Field(None, alias="api_key")
    base_url: Optional[str] = Field(None, alias="base_url")
    file_extension: Literal["mp3", "wav"] = Field("mp3", alias="file_extension")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "model": Description(
            en="Model name for the TTS server (overrides default)",
            zh="TTS 服务器的模型名称（覆盖默认值）",
        ),
        "voice": Description(
            en="Voice name(s) for the TTS server (overrides default)",
            zh="TTS 服务器的语音名称（覆盖默认值）",
        ),
        "api_key": Description(
            en="API key if required by the TTS server (overrides default)",
            zh="TTS 服务器所需的 API 密钥（覆盖默认值）",
        ),
        "base_url": Description(
            en="Base URL of the TTS server (overrides default)",
            zh="TTS 服务器的基础 URL（覆盖默认值）",
        ),
        "file_extension": Description(
            en="Audio file format (mp3 or wav, defaults to mp3)",
            zh="音频文件格式（mp3 或 wav，默认为 mp3）",
        ),
    }


class SparkTTSConfig(I18nMixin):
    """Configuration for Spark TTS."""

    api_url: str = Field(..., alias="api_url")
    prompt_wav_upload: str = Field(..., alias="prompt_wav_upload")
    api_name: str = Field(..., alias="api_name")
    gender: str = Field(..., alias="gender")
    pitch: int = Field(..., alias="pitch")
    speed: int = Field(..., alias="speed")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "prompt_wav_upload": Description(
            en="Reference audio (used when using voice cloning)",
            zh="参考音频（使用语音克隆时候使用）",
        ),
        "api_url": Description(
            en="API address of the spark tts gradio web frontend. For example: http://127.0.0.1:7860/voice_clone",
            zh="你的API地址。举例：http://127.0.0.1:7860/voice_clone",
        ),
        "api_name": Description(
            en="The API endpoint name. For example: voice_clone,voice_creation",
            zh="你的API名称。举例：voice_clone，voice_creation",
        ),
        "gender": Description(
            en="Gender of the voice (male or female)", zh="声音性别（男或女）"
        ),
        "pitch": Description(
            en="Pitch shift (in semitones) default 3,range 1-5.",
            zh="音高（以半音为单位）默认3，范围1-5",
        ),
        "speed": Description(
            en="Speed of the voice (in percent) default 3,range 1-5.",
            zh="声音速度（以百分比为单位）默认3，范围1-5",
        ),
    }


class MinimaxTTSConfig(I18nMixin):
    """Configuration for Minimax TTS."""

    group_id: str = Field(..., alias="group_id")
    api_key: str = Field(..., alias="api_key")
    model: str = Field("speech-02-turbo", alias="model")
    voice_id: str = Field("male-qn-qingse", alias="voice_id")
    pronunciation_dict: str = Field("", alias="pronunciation_dict")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "group_id": Description(en="Minimax group_id", zh="Minimax 的 group_id"),
        "api_key": Description(en="Minimax API key", zh="Minimax 的 API key"),
        "model": Description(en="Minimax model name", zh="Minimax 模型名称"),
        "voice_id": Description(en="Minimax voice id", zh="Minimax 语音 id"),
        "pronunciation_dict": Description(
            en="Custom pronunciation dictionary (string)", zh="自定义发音字典（字符串）"
        ),
    }


class ElevenLabsTTSConfig(I18nMixin):
    """Configuration for ElevenLabs TTS."""

    api_key: str = Field(..., alias="api_key")
    voice_id: str = Field(..., alias="voice_id")
    model_id: str = Field("eleven_multilingual_v2", alias="model_id")
    output_format: str = Field("mp3_44100_128", alias="output_format")
    stability: float = Field(0.5, alias="stability")
    similarity_boost: float = Field(0.5, alias="similarity_boost")
    style: float = Field(0.0, alias="style")
    use_speaker_boost: bool = Field(True, alias="use_speaker_boost")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(
            en="API key for ElevenLabs TTS service", zh="ElevenLabs TTS 服务的 API 密钥"
        ),
        "voice_id": Description(
            en="Voice ID from ElevenLabs (e.g., JBFqnCBsd6RMkjVDRZzb)",
            zh="来自 ElevenLabs 的语音 ID（如 JBFqnCBsd6RMkjVDRZzb）",
        ),
        "model_id": Description(
            en="Model ID for ElevenLabs (e.g., eleven_multilingual_v2)",
            zh="ElevenLabs 模型 ID（如 eleven_multilingual_v2）",
        ),
        "output_format": Description(
            en="Output audio format (e.g., mp3_44100_128)",
            zh="输出音频格式（如 mp3_44100_128）",
        ),
        "stability": Description(
            en="Voice stability (0.0 to 1.0)", zh="语音稳定性（0.0 到 1.0）"
        ),
        "similarity_boost": Description(
            en="Voice similarity boost (0.0 to 1.0)", zh="语音相似度增强（0.0 到 1.0）"
        ),
        "style": Description(
            en="Voice style exaggeration (0.0 to 1.0)", zh="语音风格夸张度（0.0 到 1.0）"
        ),
        "use_speaker_boost": Description(
            en="Enable speaker boost for better quality", zh="启用说话人增强以获得更好的质量"
        ),
    }


class TTSConfig(I18nMixin):
    """Configuration for Text-to-Speech."""

    tts_model: Literal[
        "azure_tts",
        "bark_tts",
        "edge_tts",
        "cosyvoice_tts",
        "cosyvoice2_tts",
        "melo_tts",
        "coqui_tts",
        "x_tts",
        "gpt_sovits_tts",
        "fish_api_tts",
        "sherpa_onnx_tts",
        "siliconflow_tts",
        "openai_tts",  # Add openai_tts here
        "spark_tts",
        "minimax_tts",
        "elevenlabs_tts",
    ] = Field(..., alias="tts_model")

    azure_tts: Optional[AzureTTSConfig] = Field(None, alias="azure_tts")
    bark_tts: Optional[BarkTTSConfig] = Field(None, alias="bark_tts")
    edge_tts: Optional[EdgeTTSConfig] = Field(None, alias="edge_tts")
    cosyvoice_tts: Optional[CosyvoiceTTSConfig] = Field(None, alias="cosyvoice_tts")
    cosyvoice2_tts: Optional[Cosyvoice2TTSConfig] = Field(None, alias="cosyvoice2_tts")
    melo_tts: Optional[MeloTTSConfig] = Field(None, alias="melo_tts")
    coqui_tts: Optional[CoquiTTSConfig] = Field(None, alias="coqui_tts")
    x_tts: Optional[XTTSConfig] = Field(None, alias="x_tts")
    gpt_sovits_tts: Optional[GPTSoVITSConfig] = Field(None, alias="gpt_sovits")
    fish_api_tts: Optional[FishAPITTSConfig] = Field(None, alias="fish_api_tts")
    sherpa_onnx_tts: Optional[SherpaOnnxTTSConfig] = Field(
        None, alias="sherpa_onnx_tts"
    )
    siliconflow_tts: Optional[SiliconFlowTTSConfig] = Field(
        None, alias="siliconflow_tts"
    )
    openai_tts: Optional[OpenAITTSConfig] = Field(None, alias="openai_tts")
    spark_tts: Optional[SparkTTSConfig] = Field(None, alias="spark_tts")
    minimax_tts: Optional[MinimaxTTSConfig] = Field(None, alias="minimax_tts")
    elevenlabs_tts: Optional[ElevenLabsTTSConfig] = Field(None, alias="elevenlabs_tts")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "tts_model": Description(
            en="Text-to-speech model to use", zh="要使用的文本转语音模型"
        ),
        "azure_tts": Description(en="Configuration for Azure TTS", zh="Azure TTS 配置"),
        "bark_tts": Description(en="Configuration for Bark TTS", zh="Bark TTS 配置"),
        "edge_tts": Description(en="Configuration for Edge TTS", zh="Edge TTS 配置"),
        "cosyvoice_tts": Description(
            en="Configuration for Cosyvoice TTS", zh="Cosyvoice TTS 配置"
        ),
        "cosyvoice2_tts": Description(
            en="Configuration for Cosyvoice2 TTS", zh="Cosyvoice2 TTS 配置"
        ),
        "melo_tts": Description(en="Configuration for Melo TTS", zh="Melo TTS 配置"),
        "coqui_tts": Description(en="Configuration for Coqui TTS", zh="Coqui TTS 配置"),
        "x_tts": Description(en="Configuration for XTTS", zh="XTTS 配置"),
        "gpt_sovits_tts": Description(
            en="Configuration for GPT-SoVITS", zh="GPT-SoVITS 配置"
        ),
        "fish_api_tts": Description(
            en="Configuration for Fish API TTS", zh="Fish API TTS 配置"
        ),
        "sherpa_onnx_tts": Description(
            en="Configuration for Sherpa Onnx TTS", zh="Sherpa Onnx TTS 配置"
        ),
        "siliconflow_tts": Description(
            en="Configuration for SiliconFlow TTS", zh="SiliconFlow TTS 配置"
        ),
        "openai_tts": Description(
            en="Configuration for OpenAI-compatible TTS", zh="OpenAI 兼容 TTS 配置"
        ),
        "spark_tts": Description(en="Configuration for Spark TTS", zh="Spark TTS 配置"),
        "minimax_tts": Description(
            en="Configuration for Minimax TTS", zh="Minimax TTS 配置"
        ),
        "elevenlabs_tts": Description(
            en="Configuration for ElevenLabs TTS", zh="ElevenLabs TTS 配置"
        ),
    }

    @model_validator(mode="after")
    def check_tts_config(cls, values: "TTSConfig", info: ValidationInfo):
        tts_model = values.tts_model

        # Only validate the selected TTS model
        if tts_model == "azure_tts" and values.azure_tts is not None:
            values.azure_tts.model_validate(values.azure_tts.model_dump())
        elif tts_model == "bark_tts" and values.bark_tts is not None:
            values.bark_tts.model_validate(values.bark_tts.model_dump())
        elif tts_model == "edge_tts" and values.edge_tts is not None:
            values.edge_tts.model_validate(values.edge_tts.model_dump())
        elif tts_model == "cosyvoice_tts" and values.cosyvoice_tts is not None:
            values.cosyvoice_tts.model_validate(values.cosyvoice_tts.model_dump())
        elif tts_model == "cosyvoice2_tts" and values.cosyvoice2_tts is not None:
            values.cosyvoice2_tts.model_validate(values.cosyvoice2_tts.model_dump())
        elif tts_model == "melo_tts" and values.melo_tts is not None:
            values.melo_tts.model_validate(values.melo_tts.model_dump())
        elif tts_model == "coqui_tts" and values.coqui_tts is not None:
            values.coqui_tts.model_validate(values.coqui_tts.model_dump())
        elif tts_model == "x_tts" and values.x_tts is not None:
            values.x_tts.model_validate(values.x_tts.model_dump())
        elif tts_model == "gpt_sovits_tts" and values.gpt_sovits_tts is not None:
            values.gpt_sovits_tts.model_validate(values.gpt_sovits_tts.model_dump())
        elif tts_model == "fish_api_tts" and values.fish_api_tts is not None:
            values.fish_api_tts.model_validate(values.fish_api_tts.model_dump())
        elif tts_model == "sherpa_onnx_tts" and values.sherpa_onnx_tts is not None:
            values.sherpa_onnx_tts.model_validate(values.sherpa_onnx_tts.model_dump())
        elif tts_model == "siliconflow_tts" and values.siliconflow_tts is not None:
            values.siliconflow_tts.model_validate(values.siliconflow_tts.model_dump())
        elif tts_model == "openai_tts" and values.openai_tts is not None:
            values.openai_tts.model_validate(values.openai_tts.model_dump())
        elif tts_model == "spark_tts" and values.spark_tts is not None:
            values.spark_tts.model_validate(values.spark_tts.model_dump())
        elif tts_model == "minimax_tts" and values.minimax_tts is not None:
            values.minimax_tts.model_validate(values.minimax_tts.model_dump())
        elif tts_model == "elevenlabs_tts" and values.elevenlabs_tts is not None:
            values.elevenlabs_tts.model_validate(values.elevenlabs_tts.model_dump())

        return values
