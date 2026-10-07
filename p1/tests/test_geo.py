import pytest
from unittest.mock import patch, AsyncMock
from backend.services.geo_service import haversine, get_route


def test_haversine_known_distance():
    # Rangia (26.47, 91.62) to Nalbari (26.44, 91.44)
    dist = haversine(26.47, 91.62, 26.44, 91.44)
    # Should be approximately 15-20 km
    assert 14.0 <= dist <= 22.0


def test_haversine_zero_distance():
    assert haversine(26.47, 91.62, 26.47, 91.62) == 0.0


def test_haversine_symmetry():
    d1 = haversine(26.47, 91.62, 26.18, 91.74)
    d2 = haversine(26.18, 91.74, 26.47, 91.62)
    assert abs(d1 - d2) < 0.001


@pytest.mark.anyio
async def test_get_route_osrm_failure_returns_haversine():
    # Mock httpx to raise a connection error
    with patch('backend.services.geo_service.httpx.AsyncClient') as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client_cls.return_value = mock_client

        result = await get_route(26.47, 91.62, 26.44, 91.44)

        assert result['routing_method'] == 'haversine'
        assert 14.0 <= result['distance_km'] <= 22.0
        assert result['duration_min'] is None
