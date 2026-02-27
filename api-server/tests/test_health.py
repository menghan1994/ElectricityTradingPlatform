import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data
