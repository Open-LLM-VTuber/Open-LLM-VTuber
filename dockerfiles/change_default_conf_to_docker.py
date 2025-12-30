from ruamel.yaml import YAML
from pathlib import Path
from loguru import logger
import re

CONFIG_FILES = [
    r"d:\OLV-Docker-Config\config_templates\conf.default.yaml",
    r"d:\OLV-Docker-Config\config_templates\conf.ZH.default.yaml"
]

OUTPUT_DIR = Path(r"d:\OLV-Docker-Config\config_templates")  # or None

yaml = YAML()
yaml.preserve_quotes = True

def replace_hosts(obj, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}"
            # skip system_config.host
            if path == "root" and k == "system_config" and isinstance(v, dict) and "host" in v:
                continue
            obj[k] = replace_hosts(v, path=new_path)
        return obj
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            obj[i] = replace_hosts(item, path=f"{path}[{i}]")
        return obj
    elif isinstance(obj, str):
        if re.search(r"(localhost|127\.0\.0\.1)", obj):
            new_val = re.sub(r"(localhost|127\.0\.0\.1)", "host.docker.internal", obj)
            logger.info(f"Replace {path}: {obj} -> {new_val}")
            return new_val
    return obj

for file_path in CONFIG_FILES:
    config_path = Path(file_path)
    if not config_path.exists():
        logger.warning(f"File not found: {config_path}")
        continue

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    data_replaced = replace_hosts(data)

    # keep system_config.host
    if data.get("system_config") and "host" in data["system_config"]:
        logger.info("keep system_config.host = 0.0.0.0")
        data_replaced["system_config"]["host"] = "0.0.0.0"

    if OUTPUT_DIR:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / config_path.name
    else:
        out_path = config_path

    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(data_replaced, f)

    logger.info(f"Config template convert to docker version finished: {config_path} -> {out_path}")
