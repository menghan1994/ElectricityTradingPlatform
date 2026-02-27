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
