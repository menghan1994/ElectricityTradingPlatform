"""StationWizardCreate schema 校验测试。"""

import pytest
from pydantic import ValidationError

from app.schemas.wizard import StationWizardCreate, WizardStorageDeviceInput


class TestWizardStorageDeviceInput:
    def test_valid_device(self):
        device = WizardStorageDeviceInput(
            name="1号储能系统",
            capacity_mwh=100.00,
            max_charge_rate_mw=50.00,
            max_discharge_rate_mw=50.00,
            soc_upper_limit=0.9,
            soc_lower_limit=0.1,
            battery_type="lfp",
        )
        assert device.name == "1号储能系统"
        assert device.battery_type == "lfp"

    def test_soc_lower_gte_upper_raises(self):
        with pytest.raises(ValidationError, match="soc_lower_limit 必须小于 soc_upper_limit"):
            WizardStorageDeviceInput(
                name="设备",
                capacity_mwh=100,
                max_charge_rate_mw=50,
                max_discharge_rate_mw=50,
                soc_upper_limit=0.1,
                soc_lower_limit=0.9,
            )

    def test_soc_equal_raises(self):
        with pytest.raises(ValidationError, match="soc_lower_limit 必须小于 soc_upper_limit"):
            WizardStorageDeviceInput(
                name="设备",
                capacity_mwh=100,
                max_charge_rate_mw=50,
                max_discharge_rate_mw=50,
                soc_upper_limit=0.5,
                soc_lower_limit=0.5,
            )

    def test_invalid_battery_type_raises(self):
        with pytest.raises(ValidationError):
            WizardStorageDeviceInput(
                name="设备",
                capacity_mwh=100,
                max_charge_rate_mw=50,
                max_discharge_rate_mw=50,
                battery_type="invalid",
            )

    def test_battery_type_none_allowed(self):
        device = WizardStorageDeviceInput(
            name="设备",
            capacity_mwh=100,
            max_charge_rate_mw=50,
            max_discharge_rate_mw=50,
        )
        assert device.battery_type is None


class TestStationWizardCreate:
    def test_valid_station_no_storage(self):
        data = StationWizardCreate(
            name="甘肃某光伏电站",
            province="gansu",
            capacity_mw=50.00,
            station_type="solar",
            has_storage=False,
        )
        assert data.name == "甘肃某光伏电站"
        assert data.storage_devices == []

    def test_valid_station_with_storage(self):
        data = StationWizardCreate(
            name="甘肃某光伏电站",
            province="gansu",
            capacity_mw=50.00,
            station_type="solar",
            grid_connection_point="330kV 某某变电站",
            has_storage=True,
            storage_devices=[
                WizardStorageDeviceInput(
                    name="1号储能",
                    capacity_mwh=100,
                    max_charge_rate_mw=50,
                    max_discharge_rate_mw=50,
                    battery_type="lfp",
                ),
            ],
        )
        assert data.has_storage is True
        assert len(data.storage_devices) == 1

    def test_has_storage_true_no_devices_raises(self):
        with pytest.raises(ValidationError, match="has_storage 为 true 时必须提供至少一个储能设备"):
            StationWizardCreate(
                name="电站",
                province="gansu",
                capacity_mw=50,
                station_type="solar",
                has_storage=True,
                storage_devices=[],
            )

    def test_has_storage_false_with_devices_raises(self):
        with pytest.raises(ValidationError, match="has_storage 为 false 时不应提供储能设备"):
            StationWizardCreate(
                name="电站",
                province="gansu",
                capacity_mw=50,
                station_type="solar",
                has_storage=False,
                storage_devices=[
                    WizardStorageDeviceInput(
                        name="设备",
                        capacity_mwh=100,
                        max_charge_rate_mw=50,
                        max_discharge_rate_mw=50,
                    ),
                ],
            )

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            StationWizardCreate(
                province="gansu",
                capacity_mw=50,
                station_type="solar",
            )

    def test_invalid_station_type_raises(self):
        with pytest.raises(ValidationError):
            StationWizardCreate(
                name="电站",
                province="gansu",
                capacity_mw=50,
                station_type="nuclear",
            )

    def test_grid_connection_point_optional(self):
        data = StationWizardCreate(
            name="电站",
            province="gansu",
            capacity_mw=50,
            station_type="solar",
        )
        assert data.grid_connection_point is None

    def test_grid_connection_point_blank_to_none(self):
        """C1: StationWizardCreate 继承 _GridConnectionPointMixin，空白字符串转 None。"""
        data = StationWizardCreate(
            name="电站",
            province="gansu",
            capacity_mw=50,
            station_type="solar",
            grid_connection_point="   ",
        )
        assert data.grid_connection_point is None

    def test_invalid_province_raises(self):
        """H6: province 字段服务端校验，不接受任意字符串。"""
        with pytest.raises(ValidationError):
            StationWizardCreate(
                name="电站",
                province="invalid_province",
                capacity_mw=50,
                station_type="solar",
            )

    def test_device_name_dedup_case_insensitive(self):
        """M1: 设备名称去重不区分大小写。"""
        with pytest.raises(ValidationError, match="储能设备名称不能重复"):
            StationWizardCreate(
                name="电站",
                province="gansu",
                capacity_mw=50,
                station_type="solar",
                has_storage=True,
                storage_devices=[
                    WizardStorageDeviceInput(
                        name="Device-A",
                        capacity_mwh=100,
                        max_charge_rate_mw=50,
                        max_discharge_rate_mw=50,
                    ),
                    WizardStorageDeviceInput(
                        name="device-a",
                        capacity_mwh=200,
                        max_charge_rate_mw=100,
                        max_discharge_rate_mw=100,
                    ),
                ],
            )
