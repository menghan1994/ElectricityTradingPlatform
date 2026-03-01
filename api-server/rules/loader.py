import importlib
import json
from pathlib import Path

RULES_DIR = Path(__file__).parent
RULES_CONFIG_DIR = RULES_DIR / "config"

_SKIP_MODULES = {"__init__", "base", "registry", "loader"}


def load_province_config(province: str) -> dict:
    """从 JSON 文件加载省份默认参数配置。"""
    config_path = RULES_CONFIG_DIR / f"{province}.json"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return json.load(f)


def load_all_province_plugins() -> None:
    """自动导入 rules/ 下所有省份模块，触发 @register_province 装饰器注册。"""
    for py_file in RULES_DIR.glob("*.py"):
        module_name = py_file.stem
        if module_name not in _SKIP_MODULES:
            importlib.import_module(f"rules.{module_name}")


def list_available_configs() -> list[str]:
    """列出所有可用的省份 JSON 配置文件名（不含扩展名）。"""
    return [f.stem for f in RULES_CONFIG_DIR.glob("*.json")]
