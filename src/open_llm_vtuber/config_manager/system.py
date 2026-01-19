# config_manager/system.py
from pydantic import Field, model_validator
from typing import Dict, ClassVar
from .i18n import I18nMixin, Description


class SystemConfig(I18nMixin):
    """System configuration settings."""

    conf_version: str = Field(..., alias="conf_version")
    host: str = Field(..., alias="host")
    port: int = Field(..., alias="port")
    config_alts_dir: str = Field(..., alias="config_alts_dir")
    tool_prompts: Dict[str, str] = Field(..., alias="tool_prompts")
    enable_proxy: bool = Field(False, alias="enable_proxy")

    # Specify namespace for this config class
    I18N_NAMESPACE: ClassVar[str] = "system"

    # Simplified DESCRIPTIONS using translation keys only
    # Translation files: locales/{en,zh,ko}/system.json
    DESCRIPTIONS: ClassVar[Dict[str, str]] = {
        "conf_version": "conf_version",
        "host": "host",
        "port": "port",
        "config_alts_dir": "config_alts_dir",
        "tool_prompts": "tool_prompts",
        "enable_proxy": "enable_proxy",
    }

    @model_validator(mode="after")
    def check_port(cls, values):
        port = values.port
        if port < 0 or port > 65535:
            raise ValueError("Port must be between 0 and 65535")
        return values
