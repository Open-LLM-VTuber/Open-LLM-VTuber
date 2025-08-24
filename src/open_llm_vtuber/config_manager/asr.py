# config_manager/asr.py
from pydantic import ValidationInfo, Field, model_validator
from typing import Literal, Optional, Dict, ClassVar
from .i18n import I18nMixin, Description


class AzureASRConfig(I18nMixin):
    """Configuration for Azure ASR service."""

    api_key: str = Field(..., alias="api_key")
    region: str = Field(..., alias="region")
    languages: list[str] = Field(["en-US", "zh-CN"], alias="languages")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(
            en="API key for Azure ASR service", zh="Azure ASR 服务的 API 密钥"
        ),
        "region": Description(
            en="Azure region (e.g., eastus)", zh="Azure 区域（如 eastus)"
        ),
        "languages": Description(
            en="List of languages to detect (e.g., ['en-US', 'zh-CN'])",
            zh="要检测的语言列表（如 ['en-US', 'zh-CN'])",
        ),
    }


class FasterWhisperConfig(I18nMixin):
    """Configuration for Faster Whisper ASR."""

    model_path: str = Field(..., alias="model_path")
    download_root: str = Field(..., alias="download_root")
    language: Optional[str] = Field(None, alias="language")
    device: str = Field("auto", alias="device")
    compute_type: Literal["int8", "float16", "float32"] = Field(
        "int8", alias="compute_type"
    )

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "model_path": Description(
            en="Path to the Faster Whisper model", zh="Faster Whisper 模型路径"
        ),
        "download_root": Description(
            en="Root directory for downloading models", zh="模型下载根目录"
        ),
        "language": Description(
            en="Language code (e.g., en, zh) or empty string for auto-detect",
            zh="语言代码（如 en, zh）或留空以自动检测",
        ),
        "device": Description(
            en="Device to use for inference (cpu, cuda, or auto)",
            zh="推理设备（cpu, cuda, auto）",
        ),
        "compute_type": Description(
            en="Compute type for the model (int8, float16, or float32)",
            zh="模型的计算类型（int8、float16 或 float32）",
        ),
    }


class WhisperCPPConfig(I18nMixin):
    """Configuration for WhisperCPP ASR."""

    model_name: str = Field(..., alias="model_name")
    model_dir: str = Field(..., alias="model_dir")
    print_realtime: bool = Field(False, alias="print_realtime")
    print_progress: bool = Field(False, alias="print_progress")
    language: str = Field("auto", alias="language")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "model_name": Description(
            en="Name of the Whisper model", zh="Whisper 模型名称"
        ),
        "model_dir": Description(
            en="Directory containing Whisper models", zh="Whisper 模型目录"
        ),
        "print_realtime": Description(
            en="Print output in real-time", zh="实时打印输出"
        ),
        "print_progress": Description(
            en="Print progress information", zh="打印进度信息"
        ),
        "language": Description(
            en="Language code (e.g., auto, en, zh)", zh="语言代码（如 auto、en、zh）"
        ),
    }


class WhisperConfig(I18nMixin):
    """Configuration for OpenAI Whisper ASR."""

    name: str = Field(..., alias="name")
    download_root: str = Field(..., alias="download_root")
    device: Literal["cpu", "cuda"] = Field("cpu", alias="device")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "name": Description(en="Name of the Whisper model", zh="Whisper 模型名称"),
        "download_root": Description(
            en="Root directory for downloading models", zh="模型下载根目录"
        ),
        "device": Description(
            en="Device to use for inference (cpu or cuda)", zh="推理设备（cpu 或 cuda）"
        ),
    }


class FunASRConfig(I18nMixin):
    """Configuration for FunASR."""

    model_name: str = Field("iic/SenseVoiceSmall", alias="model_name")
    vad_model: str = Field("fsmn-vad", alias="vad_model")
    punc_model: str = Field("ct-punc", alias="punc_model")
    device: Literal["cpu", "cuda"] = Field("cpu", alias="device")
    disable_update: bool = Field(True, alias="disable_update")
    ncpu: int = Field(4, alias="ncpu")
    hub: Literal["ms", "hf"] = Field("ms", alias="hub")
    use_itn: bool = Field(False, alias="use_itn")
    language: str = Field("auto", alias="language")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "model_name": Description(en="Name of the FunASR model", zh="FunASR 模型名称"),
        "vad_model": Description(
            en="Voice Activity Detection model", zh="语音活动检测模型"
        ),
        "punc_model": Description(en="Punctuation model", zh="标点符号模型"),
        "device": Description(
            en="Device to use for inference (cpu or cuda)", zh="推理设备（cpu 或 cuda）"
        ),
        "disable_update": Description(
            en="Disable checking for FunASR updates on launch",
            zh="启动时禁用 FunASR 更新检查",
        ),
        "ncpu": Description(
            en="Number of CPU threads for internal operations",
            zh="内部操作的 CPU 线程数",
        ),
        "hub": Description(
            en="Model hub to use (ms for ModelScope, hf for Hugging Face)",
            zh="使用的模型仓库（ms 为 ModelScope，hf 为 Hugging Face）",
        ),
        "use_itn": Description(
            en="Enable inverse text normalization", zh="启用反向文本归一化"
        ),
        "language": Description(
            en="Language code (e.g., auto, zh, en)", zh="语言代码（如 auto、zh、en）"
        ),
    }


class GroqWhisperASRConfig(I18nMixin):
    """Configuration for Groq Whisper ASR."""

    api_key: str = Field(..., alias="api_key")
    model: str = Field("whisper-large-v3-turbo", alias="model")
    lang: Optional[str] = Field(None, alias="lang")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(
            en="API key for Groq Whisper ASR", zh="Groq Whisper ASR 的 API 密钥"
        ),
        "model": Description(
            en="Name of the Groq Whisper model to use",
            zh="要使用的 Groq Whisper 模型名称",
        ),
        "lang": Description(
            en="Language code (leave empty for auto-detect)",
            zh="语言代码（留空以自动检测）",
        ),
    }


class SherpaOnnxASRConfig(I18nMixin):
    """Configuration for Sherpa Onnx ASR."""

    model_type: Literal[
        "transducer",
        "paraformer",
        "nemo_ctc",
        "wenet_ctc",
        "whisper",
        "tdnn_ctc",
        "sense_voice",
    ] = Field(..., alias="model_type")
    encoder: Optional[str] = Field(None, alias="encoder")
    decoder: Optional[str] = Field(None, alias="decoder")
    joiner: Optional[str] = Field(None, alias="joiner")
    paraformer: Optional[str] = Field(None, alias="paraformer")
    nemo_ctc: Optional[str] = Field(None, alias="nemo_ctc")
    wenet_ctc: Optional[str] = Field(None, alias="wenet_ctc")
    tdnn_model: Optional[str] = Field(None, alias="tdnn_model")
    whisper_encoder: Optional[str] = Field(None, alias="whisper_encoder")
    whisper_decoder: Optional[str] = Field(None, alias="whisper_decoder")
    sense_voice: Optional[str] = Field(None, alias="sense_voice")
    tokens: str = Field(..., alias="tokens")
    num_threads: int = Field(4, alias="num_threads")
    use_itn: bool = Field(True, alias="use_itn")
    provider: Literal["cpu", "cuda", "rocm"] = Field("cpu", alias="provider")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "model_type": Description(
            en="Type of ASR model to use", zh="要使用的 ASR 模型类型"
        ),
        "encoder": Description(
            en="Path to encoder model (for transducer)",
            zh="编码器模型路径（用于 transducer）",
        ),
        "decoder": Description(
            en="Path to decoder model (for transducer)",
            zh="解码器模型路径（用于 transducer）",
        ),
        "joiner": Description(
            en="Path to joiner model (for transducer)",
            zh="连接器模型路径（用于 transducer）",
        ),
        "paraformer": Description(
            en="Path to paraformer model", zh="Paraformer 模型路径"
        ),
        "nemo_ctc": Description(en="Path to NeMo CTC model", zh="NeMo CTC 模型路径"),
        "wenet_ctc": Description(en="Path to WeNet CTC model", zh="WeNet CTC 模型路径"),
        "tdnn_model": Description(en="Path to TDNN model", zh="TDNN 模型路径"),
        "whisper_encoder": Description(
            en="Path to Whisper encoder model", zh="Whisper 编码器模型路径"
        ),
        "whisper_decoder": Description(
            en="Path to Whisper decoder model", zh="Whisper 解码器模型路径"
        ),
        "sense_voice": Description(
            en="Path to SenseVoice model", zh="SenseVoice 模型路径"
        ),
        "tokens": Description(en="Path to tokens file", zh="词元文件路径"),
        "num_threads": Description(en="Number of threads to use", zh="使用的线程数"),
        "use_itn": Description(
            en="Enable inverse text normalization", zh="启用反向文本归一化"
        ),
        "provider": Description(
            en="Provider for inference (cpu or cuda) (cuda option needs additional settings. Please check our docs)",
            zh="推理平台（cpu 或 cuda）(cuda 需要额外配置，请参考文档)",
        ),
    }

    @model_validator(mode="after")
    def check_model_paths(cls, values: "SherpaOnnxASRConfig", info: ValidationInfo):
        model_type = values.model_type

        if model_type == "transducer":
            if not all([values.encoder, values.decoder, values.joiner, values.tokens]):
                raise ValueError(
                    "encoder, decoder, joiner, and tokens must be provided for transducer model type"
                )
        elif model_type == "paraformer":
            if not all([values.paraformer, values.tokens]):
                raise ValueError(
                    "paraformer and tokens must be provided for paraformer model type"
                )
        elif model_type == "nemo_ctc":
            if not all([values.nemo_ctc, values.tokens]):
                raise ValueError(
                    "nemo_ctc and tokens must be provided for nemo_ctc model type"
                )
        elif model_type == "wenet_ctc":
            if not all([values.wenet_ctc, values.tokens]):
                raise ValueError(
                    "wenet_ctc and tokens must be provided for wenet_ctc model type"
                )
        elif model_type == "tdnn_ctc":
            if not all([values.tdnn_model, values.tokens]):
                raise ValueError(
                    "tdnn_model and tokens must be provided for tdnn_ctc model type"
                )
        elif model_type == "whisper":
            if not all([values.whisper_encoder, values.whisper_decoder, values.tokens]):
                raise ValueError(
                    "whisper_encoder, whisper_decoder, and tokens must be provided for whisper model type"
                )
        elif model_type == "sense_voice":
            if not all([values.sense_voice, values.tokens]):
                raise ValueError(
                    "sense_voice and tokens must be provided for sense_voice model type"
                )

        return values


class ASRConfig(I18nMixin):
    """Configuration for Automatic Speech Recognition."""

    asr_model: Literal[
        "faster_whisper",
        "whisper_cpp",
        "whisper",
        "azure_asr",
        "fun_asr",
        "groq_whisper_asr",
        "sherpa_onnx_asr",
    ] = Field(..., alias="asr_model")
    azure_asr: Optional[AzureASRConfig] = Field(None, alias="azure_asr")
    faster_whisper: Optional[FasterWhisperConfig] = Field(None, alias="faster_whisper")
    whisper_cpp: Optional[WhisperCPPConfig] = Field(None, alias="whisper_cpp")
    whisper: Optional[WhisperConfig] = Field(None, alias="whisper")
    fun_asr: Optional[FunASRConfig] = Field(None, alias="fun_asr")
    groq_whisper_asr: Optional[GroqWhisperASRConfig] = Field(
        None, alias="groq_whisper_asr"
    )
    sherpa_onnx_asr: Optional[SherpaOnnxASRConfig] = Field(
        None, alias="sherpa_onnx_asr"
    )

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "asr_model": Description(
            en="Speech-to-text model to use", zh="要使用的语音识别模型"
        ),
        "azure_asr": Description(en="Configuration for Azure ASR", zh="Azure ASR 配置"),
        "faster_whisper": Description(
            en="Configuration for Faster Whisper", zh="Faster Whisper 配置"
        ),
        "whisper_cpp": Description(
            en="Configuration for WhisperCPP", zh="WhisperCPP 配置"
        ),
        "whisper": Description(en="Configuration for Whisper", zh="Whisper 配置"),
        "fun_asr": Description(en="Configuration for FunASR", zh="FunASR 配置"),
        "groq_whisper_asr": Description(
            en="Configuration for Groq Whisper ASR", zh="Groq Whisper ASR 配置"
        ),
        "sherpa_onnx_asr": Description(
            en="Configuration for Sherpa Onnx ASR", zh="Sherpa Onnx ASR 配置"
        ),
    }

    @model_validator(mode="after")
    def check_asr_config(cls, values: "ASRConfig", info: ValidationInfo):
        asr_model = values.asr_model

        # Only validate the selected ASR model
        if asr_model == "AzureASR" and values.azure_asr is not None:
            values.azure_asr.model_validate(values.azure_asr.model_dump())
        elif asr_model == "Faster-Whisper" and values.faster_whisper is not None:
            values.faster_whisper.model_validate(values.faster_whisper.model_dump())
        elif asr_model == "WhisperCPP" and values.whisper_cpp is not None:
            values.whisper_cpp.model_validate(values.whisper_cpp.model_dump())
        elif asr_model == "Whisper" and values.whisper is not None:
            values.whisper.model_validate(values.whisper.model_dump())
        elif asr_model == "FunASR" and values.fun_asr is not None:
            values.fun_asr.model_validate(values.fun_asr.model_dump())
        elif asr_model == "GroqWhisperASR" and values.groq_whisper_asr is not None:
            values.groq_whisper_asr.model_validate(values.groq_whisper_asr.model_dump())
        elif asr_model == "SherpaOnnxASR" and values.sherpa_onnx_asr is not None:
            values.sherpa_onnx_asr.model_validate(values.sherpa_onnx_asr.model_dump())

        return values
