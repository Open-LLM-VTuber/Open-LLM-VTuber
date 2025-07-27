"""
Configuration management package for Open LLM VTuber.

This package provides configuration management functionality through Pydantic models
and utility functions for loading/saving configurations.
"""

# Import main configuration classes
from .main import Config
from .system import SystemConfig
from .character import CharacterConfig
from .live import LiveConfig, BiliBiliLiveConfig
from .stateless_llm import (
    OpenAICompatibleConfig,
    ClaudeConfig,
    LlamaCppConfig,
)
from .asr import (
    ASRConfig,
    AzureASRConfig,
    FasterWhisperConfig,
    WhisperCPPConfig,
    WhisperConfig,
    FunASRConfig,
    SherpaOnnxASRConfig,
    GroqWhisperASRConfig,
)
from .tts import (
    TTSConfig,
    AzureTTSConfig,
    BarkTTSConfig,
    EdgeTTSConfig,
    CosyvoiceTTSConfig,
    MeloTTSConfig,
    CoquiTTSConfig,
    XTTSConfig,
    GPTSoVITSConfig,
    FishAPITTSConfig,
    SherpaOnnxTTSConfig,
)
from .vad import (
    VADConfig,
    SileroVADConfig,
)
from .tts_preprocessor import TTSPreprocessorConfig, TranslatorConfig, DeepLXConfig
from .i18n import I18nMixin, Description, MultiLingualString
from .agent import (
    AgentConfig,
    AgentSettings,
    StatelessLLMConfigs,
    BasicMemoryAgentConfig,
    Mem0Config,
    Mem0VectorStoreConfig,
    Mem0LLMConfig,
    Mem0EmbedderConfig,
)

# Import utility functions
from .utils import (
    read_yaml,
    validate_config,
    save_config,
    scan_config_alts_directory,
    scan_bg_directory,
)

__all__ = [
    # Main configuration classes
    "Config",
    "SystemConfig",
    "CharacterConfig",
    "LiveConfig",
    "BiliBiliLiveConfig",
    # LLM related classes
    "OpenAICompatibleConfig",
    "ClaudeConfig",
    "LlamaCppConfig",
    # Agent related classes
    "AgentConfig",
    "AgentSettings",
    "StatelessLLMConfigs",
    "BasicMemoryAgentConfig",
    "Mem0Config",
    "Mem0VectorStoreConfig",
    "Mem0LLMConfig",
    "Mem0EmbedderConfig",
    # ASR related classes
    "ASRConfig",
    "AzureASRConfig",
    "FasterWhisperConfig",
    "WhisperCPPConfig",
    "WhisperConfig",
    "FunASRConfig",
    "SherpaOnnxASRConfig",
    "GroqWhisperASRConfig",
    # TTS related classes
    "TTSConfig",
    "AzureTTSConfig",
    "BarkTTSConfig",
    "EdgeTTSConfig",
    "CosyvoiceTTSConfig",
    "MeloTTSConfig",
    "CoquiTTSConfig",
    "XTTSConfig",
    "GPTSoVITSConfig",
    "FishAPITTSConfig",
    "SherpaOnnxTTSConfig",
    # VAD related classes
    "VADConfig",
    "SileroVADConfig",
    # TTS preprocessor related classes
    "TTSPreprocessorConfig",
    "TranslatorConfig",
    "DeepLXConfig",
    # i18n related classes
    "I18nMixin",
    "Description",
    "MultiLingualString",
    # Utility functions
    "read_yaml",
    "validate_config",
    "save_config",
    "scan_config_alts_directory",
    "scan_bg_directory",
]
