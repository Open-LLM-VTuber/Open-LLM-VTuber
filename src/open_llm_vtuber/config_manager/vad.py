# config_manager/vad.py
from pydantic import ValidationInfo, Field, model_validator
from typing import Literal, Optional, Dict, ClassVar
from .i18n import I18nMixin, Description


class SileroVADConfig(I18nMixin):
    """Configuration for Silero VAD service."""

    orig_sr: int = Field(..., alias="orig_sr")  # 16000
    target_sr: int = Field(..., alias="target_sr")  # 16000
    prob_threshold: float = Field(..., alias="prob_threshold")  # 0.4
    db_threshold: int = Field(..., alias="db_threshold")  # 60
    required_hits: int = Field(..., alias="required_hits")  # 3 * (0.032) = 0.1s
    required_misses: int = Field(..., alias="required_misses")  # 24 * (0.032) = 0.8s
    smoothing_window: int = Field(..., alias="smoothing_window")  # 5

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "orig_sr": Description(en="Original Audio Sample Rate", zh="原始音频采样率"),
        "target_sr": Description(en="Target Audio Sample Rate", zh="目标音频采样率"),
        "prob_threshold": Description(
            en="Probability Threshold for VAD", zh="语音活动检测的概率阈值"
        ),
        "db_threshold": Description(
            en="Decibel Threshold for VAD", zh="语音活动检测的分贝阈值"
        ),
        "required_hits": Description(
            en="Number of consecutive hits required to consider speech",
            zh="连续命中次数以确认语音",
        ),
        "required_misses": Description(
            en="Number of consecutive misses required to consider silence",
            zh="连续未命中次数以确认静音",
        ),
        "smoothing_window": Description(
            en="Smoothing window size for VAD", zh="语音活动检测的平滑窗口大小"
        ),
    }


class VADConfig(I18nMixin):
    """Configuration for Automatic Speech Recognition."""

    vad_model: Optional[Literal["silero_vad"]] = Field(None, alias="vad_model")
    silero_vad: Optional[SileroVADConfig] = Field(None, alias="silero_vad")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "vad_model": Description(
            en="Voice Activity Detection model to use", zh="要使用的语音活动检测模型"
        ),
        "silero_vad": Description(
            en="Configuration for Silero VAD", zh="Silero VAD 配置"
        ),
    }

    @model_validator(mode="after")
    def check_asr_config(cls, values: "VADConfig", info: ValidationInfo):
        vad_model = values.silero_vad

        # Only validate the selected ASR model
        if vad_model == "silero_vad" and values.silero_vad is not None:
            values.silero_vad.model_validate(values.silero_vad.model_dump())

        return values
