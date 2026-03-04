from app.services.ems_adapters.base import BaseEmsAdapter
from app.services.ems_adapters.catl import CatlEmsAdapter
from app.services.ems_adapters.huawei import HuaweiEmsAdapter
from app.services.ems_adapters.standard import StandardEmsAdapter
from app.services.ems_adapters.sungrow import SungrowEmsAdapter

_ADAPTERS: dict[str, type[BaseEmsAdapter]] = {
    "standard": StandardEmsAdapter,
    "sungrow": SungrowEmsAdapter,
    "huawei": HuaweiEmsAdapter,
    "catl": CatlEmsAdapter,
}


def get_adapter(ems_format: str) -> BaseEmsAdapter:
    """根据 ems_format 返回对应的适配器实例。"""
    adapter_cls = _ADAPTERS.get(ems_format)
    if adapter_cls is None:
        raise ValueError(f"不支持的 EMS 格式: {ems_format}")
    return adapter_cls()
