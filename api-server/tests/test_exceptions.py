import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import BusinessError
from app.main import app


@pytest.mark.asyncio
async def test_business_error_format():
    error = BusinessError(
        code="TEST_ERROR",
        message="测试错误",
        detail="详细信息",
        status_code=400,
    )
    assert error.code == "TEST_ERROR"
    assert error.message == "测试错误"
    assert error.detail == "详细信息"
    assert error.status_code == 400


@pytest.mark.asyncio
async def test_business_error_dict_detail():
    error = BusinessError(
        code="STATION_NOT_FOUND",
        message="电站不存在",
        detail={"station_id": 999},
        status_code=404,
    )
    assert error.code == "STATION_NOT_FOUND"
    assert error.detail == {"station_id": 999}
    assert error.status_code == 404
