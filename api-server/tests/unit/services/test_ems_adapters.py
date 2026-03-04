from decimal import Decimal

import pytest

from app.services.ems_adapters import get_adapter
from app.services.ems_adapters.catl import CatlEmsAdapter
from app.services.ems_adapters.huawei import HuaweiEmsAdapter
from app.services.ems_adapters.standard import StandardEmsAdapter
from app.services.ems_adapters.sungrow import SungrowEmsAdapter


class TestGetAdapterFactory:
    """get_adapter 工厂方法测试。"""

    def test_returns_standard_adapter(self):
        adapter = get_adapter("standard")
        assert isinstance(adapter, StandardEmsAdapter)

    def test_returns_sungrow_adapter(self):
        adapter = get_adapter("sungrow")
        assert isinstance(adapter, SungrowEmsAdapter)

    def test_returns_huawei_adapter(self):
        adapter = get_adapter("huawei")
        assert isinstance(adapter, HuaweiEmsAdapter)

    def test_returns_catl_adapter(self):
        adapter = get_adapter("catl")
        assert isinstance(adapter, CatlEmsAdapter)

    def test_unsupported_format_raises(self):
        with pytest.raises(ValueError, match="不支持的 EMS 格式"):
            get_adapter("unknown_vendor")


class TestStandardEmsAdapter:
    """标准格式适配器测试。"""

    def test_column_mapping(self):
        adapter = StandardEmsAdapter()
        mapping = adapter.get_column_mapping()
        assert mapping["trading_date"] == "trading_date"
        assert mapping["period"] == "period"
        assert mapping["soc"] == "soc"
        assert mapping["charge_power_kw"] == "charge_power_kw"
        assert mapping["discharge_power_kw"] == "discharge_power_kw"
        assert mapping["cycle_count"] == "cycle_count"

    def test_transform_soc_passthrough(self):
        adapter = StandardEmsAdapter()
        assert adapter.transform_soc("0.85") == Decimal("0.85")

    def test_transform_power_passthrough(self):
        adapter = StandardEmsAdapter()
        assert adapter.transform_power("150.5") == Decimal("150.5")

    def test_transform_cycle_count(self):
        adapter = StandardEmsAdapter()
        assert adapter.transform_cycle_count("200") == 200
        assert adapter.transform_cycle_count(100) == 100


class TestSungrowEmsAdapter:
    """阳光电源格式适配器测试。"""

    def test_column_mapping_chinese_names(self):
        adapter = SungrowEmsAdapter()
        mapping = adapter.get_column_mapping()
        assert mapping["数据日期"] == "trading_date"
        assert mapping["时段序号"] == "period"
        assert mapping["SOC(%)"] == "soc"
        assert mapping["充电功率(kW)"] == "charge_power_kw"
        assert mapping["放电功率(kW)"] == "discharge_power_kw"
        assert mapping["累计循环"] == "cycle_count"

    def test_transform_soc_percentage_to_decimal(self):
        """阳光电源 SOC 为百分比 (0-100)，需除以 100 转换为小数 (0-1)。"""
        adapter = SungrowEmsAdapter()
        assert adapter.transform_soc("85") == Decimal("0.85")
        assert adapter.transform_soc("100") == Decimal("1")
        assert adapter.transform_soc("0") == Decimal("0")
        assert adapter.transform_soc(50.5) == Decimal("0.505")

    def test_transform_soc_boundary_values(self):
        adapter = SungrowEmsAdapter()
        assert adapter.transform_soc("0") == Decimal("0")
        assert adapter.transform_soc("100") == Decimal("1")


class TestHuaweiEmsAdapter:
    """华为格式适配器测试。"""

    def test_column_mapping_pascal_case(self):
        adapter = HuaweiEmsAdapter()
        mapping = adapter.get_column_mapping()
        assert mapping["Date"] == "trading_date"
        assert mapping["TimeSlot"] == "period"
        assert mapping["BatterySOC"] == "soc"
        assert mapping["ChargePower"] == "charge_power_kw"
        assert mapping["DischargePower"] == "discharge_power_kw"
        assert mapping["CycleCount"] == "cycle_count"

    def test_transform_soc_passthrough(self):
        """华为 SOC 已为小数格式，无需特殊转换。"""
        adapter = HuaweiEmsAdapter()
        assert adapter.transform_soc("0.85") == Decimal("0.85")


class TestCatlEmsAdapter:
    """宁德时代格式适配器测试。"""

    def test_column_mapping_snake_case(self):
        adapter = CatlEmsAdapter()
        mapping = adapter.get_column_mapping()
        assert mapping["record_date"] == "trading_date"
        assert mapping["period_no"] == "period"
        assert mapping["soc_pct"] == "soc"
        assert mapping["charge_kw"] == "charge_power_kw"
        assert mapping["discharge_kw"] == "discharge_power_kw"
        assert mapping["total_cycles"] == "cycle_count"

    def test_transform_soc_percentage_to_decimal(self):
        """宁德时代 soc_pct 为百分比 (0-100)，需除以 100 转换为小数 (0-1)。"""
        adapter = CatlEmsAdapter()
        assert adapter.transform_soc("85") == Decimal("0.85")
        assert adapter.transform_soc("100") == Decimal("1")
        assert adapter.transform_soc("0") == Decimal("0")


class TestAllAdaptersHaveRequiredColumns:
    """所有适配器必须映射到6个标准列。"""

    REQUIRED_STANDARD_COLUMNS = {
        "trading_date", "period", "soc",
        "charge_power_kw", "discharge_power_kw", "cycle_count",
    }

    @pytest.mark.parametrize("ems_format", ["standard", "sungrow", "huawei", "catl"])
    def test_mapping_covers_all_standard_columns(self, ems_format):
        adapter = get_adapter(ems_format)
        mapping = adapter.get_column_mapping()
        mapped_targets = set(mapping.values())
        assert mapped_targets == self.REQUIRED_STANDARD_COLUMNS
