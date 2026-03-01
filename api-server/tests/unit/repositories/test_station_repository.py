"""StationRepository 单元测试 — Mock 数据库会话，验证 Repository 操作。"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.station import PowerStation
from app.repositories.station import StationRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def station_repo(mock_session):
    return StationRepository(mock_session)


def _make_station(**kwargs):
    defaults = {
        "id": uuid4(),
        "name": "测试电站",
        "province": "广东",
        "capacity_mw": Decimal("100.00"),
        "station_type": "wind",
        "grid_connection_point": None,
        "has_storage": False,
        "is_active": True,
    }
    defaults.update(kwargs)
    station = MagicMock(spec=PowerStation)
    for k, v in defaults.items():
        setattr(station, k, v)
    return station


class TestGetByName:
    @pytest.mark.asyncio
    async def test_returns_station_when_found(self, station_repo, mock_session):
        station = _make_station()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = station
        mock_session.execute.return_value = mock_result

        result = await station_repo.get_by_name("测试电站")

        assert result is station
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, station_repo, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await station_repo.get_by_name("不存在")

        assert result is None


class TestGetAllActive:
    @pytest.mark.asyncio
    async def test_returns_active_stations(self, station_repo, mock_session):
        stations = [_make_station(name=f"电站{i}") for i in range(3)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = stations
        mock_session.execute.return_value = mock_result

        result = await station_repo.get_all_active()

        assert len(result) == 3
        mock_session.execute.assert_called_once()


class TestGetByIds:
    @pytest.mark.asyncio
    async def test_returns_matching_stations(self, station_repo, mock_session):
        stations = [_make_station(name=f"电站{i}") for i in range(2)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = stations
        mock_session.execute.return_value = mock_result

        result = await station_repo.get_by_ids([stations[0].id, stations[1].id])

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_ids(self, station_repo, mock_session):
        result = await station_repo.get_by_ids([])

        assert result == []
        mock_session.execute.assert_not_called()


class TestGetAllPaginated:
    @pytest.mark.asyncio
    async def test_returns_paginated_results(self, station_repo, mock_session):
        stations = [_make_station(name=f"电站{i}") for i in range(2)]

        count_result = MagicMock()
        count_result.scalar_one.return_value = 10

        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = stations

        mock_session.execute.side_effect = [count_result, list_result]

        result, total = await station_repo.get_all_paginated(page=1, page_size=20)

        assert len(result) == 2
        assert total == 10

    @pytest.mark.asyncio
    async def test_limits_page_size_to_100(self, station_repo, mock_session):
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [count_result, list_result]

        await station_repo.get_all_paginated(page=1, page_size=999)

        # Verify the list query (second call) has LIMIT 100, not 999
        list_stmt = mock_session.execute.call_args_list[1][0][0]
        compiled = list_stmt.compile(compile_kwargs={"literal_binds": True})
        sql_str = str(compiled)
        assert "LIMIT 100" in sql_str, f"Expected LIMIT 100 in SQL, got: {sql_str}"


class TestGetAllPaginatedFiltered:
    @pytest.mark.asyncio
    async def test_no_filter_returns_all(self, station_repo, mock_session):
        """allowed_station_ids=None → 不过滤"""
        stations = [_make_station(name=f"电站{i}") for i in range(2)]
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = stations
        mock_session.execute.side_effect = [count_result, list_result]

        result, total = await station_repo.get_all_paginated_filtered(
            allowed_station_ids=None, page=1, page_size=20,
        )
        assert len(result) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_empty_ids_returns_empty(self, station_repo, mock_session):
        """allowed_station_ids=[] → 快速返回空结果"""
        result, total = await station_repo.get_all_paginated_filtered(
            allowed_station_ids=[], page=1, page_size=20,
        )
        assert result == []
        assert total == 0
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_with_allowed_ids_adds_filter(self, station_repo, mock_session):
        """allowed_station_ids=[...] → WHERE IN 过滤"""
        sid = uuid4()
        stations = [_make_station(id=sid)]
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = stations
        mock_session.execute.side_effect = [count_result, list_result]

        result, total = await station_repo.get_all_paginated_filtered(
            allowed_station_ids=[sid], page=1, page_size=20,
        )
        assert len(result) == 1
        assert total == 1


class TestGetAllActiveFiltered:
    @pytest.mark.asyncio
    async def test_no_filter(self, station_repo, mock_session):
        stations = [_make_station()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = stations
        mock_session.execute.return_value = mock_result

        result = await station_repo.get_all_active_filtered(allowed_station_ids=None)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_empty_ids_returns_empty(self, station_repo, mock_session):
        result = await station_repo.get_all_active_filtered(allowed_station_ids=[])
        assert result == []
        mock_session.execute.assert_not_called()


class TestHasActiveBindings:
    @pytest.mark.asyncio
    async def test_returns_true_when_bindings_exist(self, station_repo, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 3
        mock_session.execute.return_value = mock_result

        result = await station_repo.has_active_bindings(uuid4())

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_bindings(self, station_repo, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        result = await station_repo.has_active_bindings(uuid4())

        assert result is False
