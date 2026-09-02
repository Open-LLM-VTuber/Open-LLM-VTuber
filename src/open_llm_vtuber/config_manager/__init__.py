"""
Configuration management package for Open LLM VTuber.

This package provides configuration management functionality through Pydantic models
and utility functions for loading/saving configurations.
"""

# Import main configuration classes
from .agent import (
    AgentConfig,
    AgentSettings,
    BasicMemoryAgentConfig,
    Mem0Config,
    Mem0EmbedderConfig,
    Mem0LLMConfig,
    Mem0VectorStoreConfig,
    StatelessLLMConfigs,
)
from .asr import (
    ASRConfig,
    AzureASRConfig,
    FasterWhisperConfig,
    FunASRConfig,
    GroqWhisperASRConfig,
    SherpaOnnxASRConfig,
    WhisperConfig,
    WhisperCPPConfig,
)
from .character import CharacterConfig
from .i18n import Description, I18nMixin, MultiLingualString
from .live import BiliBiliLiveConfig, LiveConfig
from .main import Config
from .stateless_llm import (
    ClaudeConfig,
    LlamaCppConfig,
    OpenAICompatibleConfig,
)
from .system import SystemConfig
from .tts import (
    AzureTTSConfig,
    BarkTTSConfig,
    CoquiTTSConfig,
    CosyvoiceTTSConfig,
    EdgeTTSConfig,
    FishAPITTSConfig,
    GPTSoVITSConfig,
    MeloTTSConfig,
    SherpaOnnxTTSConfig,
    TTSConfig,
    XTTSConfig,
)
from .tts_preprocessor import DeepLXConfig, TranslatorConfig, TTSPreprocessorConfig

# Import utility functions
from .utils import (
    read_yaml,
    save_config,
    scan_bg_directory,
    scan_config_alts_directory,
    validate_config,
)
from .vad import (
    SileroVADConfig,
    VADConfig,
)

__all__ = [
    # ASR related classes
    "ASRConfig",
    # Agent related classes
    "AgentConfig",
    "AgentSettings",
    "AzureASRConfig",
    "AzureTTSConfig",
    "BarkTTSConfig",
    "BasicMemoryAgentConfig",
    "BiliBiliLiveConfig",
    "CharacterConfig",
    "ClaudeConfig",
    # Main configuration classes
    "Config",
    "CoquiTTSConfig",
    "CosyvoiceTTSConfig",
    "DeepLXConfig",
    "Description",
    "EdgeTTSConfig",
    "FasterWhisperConfig",
    "FishAPITTSConfig",
    "FunASRConfig",
    "GPTSoVITSConfig",
    "GroqWhisperASRConfig",
    # i18n related classes
    "I18nMixin",
    "LiveConfig",
    "LlamaCppConfig",
    "MeloTTSConfig",
    "Mem0Config",
    "Mem0EmbedderConfig",
    "Mem0LLMConfig",
    "Mem0VectorStoreConfig",
    "MultiLingualString",
    # LLM related classes
    "OpenAICompatibleConfig",
    "SherpaOnnxASRConfig",
    "SherpaOnnxTTSConfig",
    "SileroVADConfig",
    "StatelessLLMConfigs",
    "SystemConfig",
    # TTS related classes
    "TTSConfig",
    # TTS preprocessor related classes
    "TTSPreprocessorConfig",
    "TranslatorConfig",
    # VAD related classes
    "VADConfig",
    "WhisperCPPConfig",
    "WhisperConfig",
    "XTTSConfig",
    # Utility functions
    "read_yaml",
    "save_config",
    "scan_bg_directory",
    "scan_config_alts_directory",
    "validate_config",
]
