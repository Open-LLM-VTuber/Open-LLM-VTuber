# config_manager/llm.py
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationInfo
from typing import Literal, Optional, Dict, ClassVar, Union, Any
from .i18n import I18nMixin, Description, MultiLingualString

# --- Sub-models for specific LLM providers ---


class OllamaConfig(I18nMixin):
    base_url: str = Field("http://localhost:11434/v1", alias="BASE_URL")
    llm_api_key: Optional[str] = Field(None, alias="LLM_API_KEY")
    organization_id: Optional[str] = Field(None, alias="ORGANIZATION_ID")
    project_id: Optional[str] = Field(None, alias="PROJECT_ID")
    model: str = Field(..., alias="MODEL")
    verbose: bool = Field(False, alias="VERBOSE")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "base_url": Description.from_str("Base URL for the Ollama API"),
        "llm_api_key": Description.from_str("API key for the LLM"),
        "organization_id": Description.from_str("Organization ID"),
        "project_id": Description.from_str("Project ID"),
        "model": Description.from_str("Name of the LLM model to use"),
        "verbose": Description.from_str("Enable verbose output"),
    }


class ClaudeConfig(I18nMixin):
    base_url: str = Field("https://api.anthropic.com", alias="BASE_URL")
    llm_api_key: str = Field(..., alias="LLM_API_KEY")
    model: str = Field("claude-3-haiku-20240307", alias="MODEL")
    verbose: bool = Field(False, alias="VERBOSE")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "base_url": Description.from_str("Base URL for the Claude API"),
        "llm_api_key": Description.from_str("API key for the Claude LLM"),
        "model": Description.from_str("Name of the Claude model to use"),
        "verbose": Description.from_str("Enable verbose output"),
    }


class LlamaCPPConfig(I18nMixin):
    model_path: str = Field(..., alias="MODEL_PATH")
    verbose: bool = Field(True, alias="VERBOSE")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "model_path": Description.from_str("Path to the GGUF model file"),
        "verbose": Description.from_str("Enable verbose output"),
    }


class VectorStoreConfig(I18nMixin):
    provider: Literal["qdrant"] = Field(..., alias="provider")
    config: Dict[str, Any] = Field(..., alias="config")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "provider": Description.from_str("Provider of vector store"),
        "config": Description.from_str("Configuration for the vector store provider"),
    }


class EmbedderConfig(I18nMixin):
    provider: Literal["ollama"] = Field(..., alias="provider")
    config: Dict[str, Any] = Field(..., alias="config")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "provider": Description.from_str("Provider of embedder"),
        "config": Description.from_str("Configuration for the embedder provider"),
    }


class Mem0Config(I18nMixin):
    user_id: str = Field("user-0", alias="USER_ID")
    base_url: str = Field("http://localhost:11434/v1", alias="BASE_URL")
    llm_api_key: Optional[str] = Field(None, alias="LLM_API_KEY")
    organization_id: Optional[str] = Field(None, alias="ORGANIZATION_ID")
    project_id: Optional[str] = Field(None, alias="PROJECT_ID")
    model: str = Field("llama3.1:latest", alias="MODEL")
    verbose: bool = Field(False, alias="VERBOSE")
    vector_store: Optional[VectorStoreConfig] = Field(None, alias="vector_store")
    llm: Optional[OllamaConfig] = Field(None, alias="llm")
    embedder: Optional[EmbedderConfig] = Field(None, alias="embedder")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "user_id": Description.from_str("User ID for Mem0"),
        "base_url": Description.from_str("Base URL for the Mem0 API"),
        "llm_api_key": Description.from_str("API key for the LLM"),
        "organization_id": Description.from_str("Organization ID"),
        "project_id": Description.from_str("Project ID"),
        "model": Description.from_str("Name of the LLM model to use"),
        "verbose": Description.from_str("Enable verbose output"),
        "vector_store": Description.from_str("Configuration for the vector store"),
        "llm": Description.from_str("Configuration for the LLM"),
        "embedder": Description.from_str("Configuration for the embedder"),
    }

    @model_validator(mode="after")
    def check_mem0_fields(cls, values: "Mem0Config", info: ValidationInfo):
        # Access the llm_provider from the parent LLMConfig
        llm_provider = info.context.get("llm_provider") if info.context else None

        if llm_provider == "mem0":
            if values.vector_store is None:
                raise ValueError(
                    "vector_store must be provided when llm_provider is 'mem0'"
                )
            if values.llm is None:
                raise ValueError(
                    "llm configuration must be provided when llm_provider is 'mem0'"
                )
            if values.embedder is None:
                raise ValueError(
                    "embedder configuration must be provided when llm_provider is 'mem0'"
                )
        return values


class MemGPTConfig(I18nMixin):
    base_url: str = Field("http://localhost:8283", alias="BASE_URL")
    admin_token: str = Field(..., alias="ADMIN_TOKEN")
    agent_id: str = Field(..., alias="AGENT_ID")
    verbose: bool = Field(True, alias="VERBOSE")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "base_url": Description.from_str("Base URL for the MemGPT server"),
        "admin_token": Description.from_str(
            "Admin server password for MemGPT (found in MemGPT console output)"
        ),
        "agent_id": Description.from_str("ID of the agent to send the message to"),
        "verbose": Description.from_str("Enable verbose output"),
    }


# --- Main LLMConfig model ---


class LLMConfig(I18nMixin):
    """
    Configuration for the Language Learning Model.
    """

    llm_provider: Literal["ollama", "memgpt", "mem0", "claude", "llamacpp"] = Field(
        ..., alias="LLM_PROVIDER"
    )
    ollama: Optional[OllamaConfig] = Field(None, alias="ollama")
    claude: Optional[ClaudeConfig] = Field(None, alias="claude")
    llamacpp: Optional[LlamaCPPConfig] = Field(None, alias="llamacpp")
    mem0: Optional[Mem0Config] = Field(None, alias="mem0")
    memgpt: Optional[MemGPTConfig] = Field(None, alias="memgpt")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "llm_provider": Description.from_str(
            "Provider of LLM",
            "Options: 'ollama' (for any OpenAI Compatible backend), 'memgpt' (requires setup), 'mem0', 'claude', 'llamacpp'",
        ),
        "ollama": Description.from_str(
            "Configuration for Ollama & OpenAI Compatible inference backend"
        ),
        "claude": Description.from_str("Configuration for Claude API"),
        "llamacpp": Description.from_str("Configuration for llamacpp"),
        "mem0": Description.from_str("Configuration for Mem0"),
        "memgpt": Description.from_str("Configuration for MemGPT"),
    }

    @model_validator(mode="after")
    def check_provider_config(cls, values: "LLMConfig", info: ValidationInfo):
        provider = values.llm_provider

        # Only validate the selected provider
        if provider == "ollama" and values.ollama is not None:
            values.ollama.model_validate(values.ollama.model_dump())
        elif provider == "claude" and values.claude is not None:
            values.claude.model_validate(values.claude.model_dump())
        elif provider == "llamacpp" and values.llamacpp is not None:
            values.llamacpp.model_validate(values.llamacpp.model_dump())
        elif provider == "mem0" and values.mem0 is not None:
            values.mem0.model_validate(values.mem0.model_dump(), context={"llm_provider": provider})
        elif provider == "memgpt" and values.memgpt is not None:
            values.memgpt.model_validate(values.memgpt.model_dump())

        return values