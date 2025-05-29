# config_manager/system.py
from pydantic import Field, model_validator
from typing import Dict, ClassVar
from .i18n import I18nMixin, Description
from pydantic import BaseModel, Field
from typing import Dict, ClassVar, Optional
from .i18n import I18nMixin, Description


class ElasticsearchConfig(I18nMixin, BaseModel):
    """Elasticsearch configuration."""

    enabled: bool = Field(False, alias="enabled")
    host: str = Field("http://localhost:9200", alias="host")
    user: str = Field("elastic", alias="user")
    password: str = Field("", alias="password")
    index: str = Field("faqs", alias="index")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "enabled": Description(
            en="Enable Elasticsearch FAQ matching",
            zh="启用Elasticsearch FAQ匹配"
        ),
        "host": Description(
            en="Elasticsearch host URL",
            zh="Elasticsearch主机地址"
        ),
        "user": Description(
            en="Elasticsearch username",
            zh="Elasticsearch用户名"
        ),
        "password": Description(
            en="Elasticsearch password",
            zh="Elasticsearch密码"
        ),
        "index": Description(
            en="FAQ index name",
            zh="FAQ索引名称"
        )
    }


class SystemConfig(I18nMixin, BaseModel):
    """System configuration settings."""

    conf_version: str = Field(..., alias="conf_version")
    host: str = Field(..., alias="host")
    port: int = Field(..., alias="port")
    config_alts_dir: str = Field(..., alias="config_alts_dir")
    tool_prompts: Dict[str, str] = Field(..., alias="tool_prompts")
    es_config: ElasticsearchConfig = Field(
        ElasticsearchConfig(), alias="es_config"
    )

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "conf_version": Description(en="Configuration version", zh="配置文件版本"),
        "host": Description(
            en="Server host, '0.0.0.0' to listen on all interfaces; use '127.0.0.1' for local access only",
            zh="服务器主机，'0.0.0.0'表示监听所有网络接口；如果需要安全，可以使用'127.0.0.1'（仅本地访问）",
        ),
        "port": Description(en="Server port number", zh="服务器端口号"),
        "config_alts_dir": Description(
            en="Directory for alternative configurations", zh="备用配置目录"
        ),
        "tool_prompts": Description(
            en="Tool prompts to be inserted into persona prompt",
            zh="要插入到角色提示词中的工具提示词",
        ),
        "es_config": Description(
            en="Elasticsearch configuration for FAQ matching",
            zh="Elasticsearch FAQ匹配配置"
        ),
    }

    @model_validator(mode="after")
    def check_port(cls, values):
        port = values.port
        if port < 0 or port > 65535:
            raise ValueError("Port must be between 0 and 65535")
        return values