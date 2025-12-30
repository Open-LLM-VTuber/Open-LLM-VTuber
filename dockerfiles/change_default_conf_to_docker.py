from ruamel.yaml import YAML
from pathlib import Path
import shutil
from loguru import logger

# 可以是单个文件或文件列表
CONFIG_FILES = [
    r"d:\OLV-Docker-Config\config_templates\conf.default.yaml",
    r"d:\OLV-Docker-Config\config_templates\conf.ZH.default.yaml"
]

# 可选输出目录，如果为 None 则覆盖原文件
OUTPUT_DIR = Path(r"d:\OLV-Docker-Config\config_templates")  # 或 None

yaml = YAML()
yaml.preserve_quotes = True

import re

def replace_hosts(obj, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}"
            # 跳过 system_config.host
            if path == "root" and k == "system_config" and isinstance(v, dict) and "host" in v:
                continue
            obj[k] = replace_hosts(v, path=new_path)
        return obj
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            obj[i] = replace_hosts(item, path=f"{path}[{i}]")
        return obj
    elif isinstance(obj, str):
        # 模糊匹配替换
        if re.search(r"(localhost|127\.0\.0\.1)", obj):
            new_val = re.sub(r"(localhost|127\.0\.0\.1)", "host.docker.internal", obj)
            logger.info(f"替换字段 {path}: {obj} -> {new_val}")
            return new_val
    return obj

for file_path in CONFIG_FILES:
    config_path = Path(file_path)
    if not config_path.exists():
        logger.warning(f"文件不存在: {config_path}")
        continue

    # 读取 YAML
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    # 替换所有 host 字段
    data_replaced = replace_hosts(data)

    # 保留 system_config.host
    if data.get("system_config") and "host" in data["system_config"]:
        logger.info(f"保留 system_config.host = 0.0.0.0")
        data_replaced["system_config"]["host"] = "0.0.0.0"

    # 确定输出路径
    if OUTPUT_DIR:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / config_path.name
    else:
        out_path = config_path

    # 写回 YAML
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(data_replaced, f)

    logger.info(f"文件处理完成: {config_path} -> {out_path}")
