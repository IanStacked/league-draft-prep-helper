from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from utils import (
    RateLimitError,
    UserNotFoundError,
    call_riot_api,
    get_puuid,
    get_ranked_info,
    parse_riot_id,
)

# Tests for Helper Functions


def test_parse_riot_id_valid():
    assert parse_riot_id("Ninja#TAG") == ("Ninja", "tag")  # capitalized tag
    assert parse_riot_id("Ninja#tag") == ("Ninja", "tag")  # lowercase tag
    assert parse_riot_id("NiNJa#TaG") == ("NiNJa", "tag")  # random caps


def test_parse_riot_id_invalid():
    assert parse_riot_id("NinjaTag") is None  # no hashtag
    assert parse_riot_id("Ninja#") is None  # no tag
    assert parse_riot_id("#tag") is None  # no username


# Tests for API Functions


@pytest.fixture
def mock_session():
    session = MagicMock()
    context_manager = MagicMock()
    response = AsyncMock()
    response.status = 200
    response.json.return_value = {}
    context_manager.__aenter__.return_value = response
    context_manager.__aexit__.return_value = None
    session.get.return_value = context_manager
    return session


@pytest.mark.asyncio
async def test_get_puuid_success(mock_session):
    mock_response = mock_session.get.return_value.__aenter__.return_value
    mock_response.json.return_value = {"puuid": "12345"}
    result = await get_puuid(mock_session, "Name", "Tag", "KEY")
    assert result == "12345"


@pytest.mark.asyncio
async def test_get_ranked_info_success(mock_session):
    test_data = [
        {
            "queueType": "RANKED_FLEX_SR",
            "tier": "SILVER",
            "rank": "I",
            "leaguePoints": 10,
        },
        {
            "queueType": "RANKED_SOLO_5x5",
            "tier": "GOLD",
            "rank": "IV",
            "leaguePoints": 20,
        },
    ]
    mock_response = mock_session.get.return_value.__aenter__.return_value
    mock_response.json.return_value = test_data
    result = await get_ranked_info(mock_session, "puuid", "KEY")
    assert result["tier"] == "GOLD"
    assert result["rank"] == "IV"
    assert result["LP"] == 20


@pytest.mark.asyncio
async def test_get_ranked_info_unranked(mock_session):
    mock_response = mock_session.get.return_value.__aenter__.return_value
    mock_response.json.return_value = (
        ""  # not None, as that is what is returned for an invalid puuid
    )
    result = await get_ranked_info(mock_session, "puuid", "KEY")
    assert result["tier"] == "UNRANKED"
    assert result["rank"] == ""
    assert result["LP"] == 0


@pytest.mark.asyncio
async def test_get_ranked_info_invalid_puuid(mock_session):
    mock_response = mock_session.get.return_value.__aenter__.return_value
    mock_response.status = 404
    mock_response.json.return_value = None
    with pytest.raises(UserNotFoundError):
        await get_ranked_info(mock_session, "puuid", "KEY")


@pytest.mark.asyncio
async def test_api_rate_limit_retry(mock_session):
    response_429 = AsyncMock()
    response_429.status = 429
    response_429.headers = {"Retry-After": "1"}
    response_200 = AsyncMock()
    response_200.status = 200
    response_200.json.return_value = {"key": "value"}
    mock_context = mock_session.get.return_value
    mock_context.__aenter__.side_effect = [response_429, response_200]
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await call_riot_api(mock_session, "htpps://fakeurl.com", {})
        assert result == {"key": "value"}
        assert mock_session.get.call_count == 2
        mock_sleep.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_api_rate_limit_max_retries_exceeded(mock_session):
    response_429 = AsyncMock()
    response_429.status = 429
    response_429.headers = {"Retry-After": "1"}
    mock_context = mock_session.get.return_value
    mock_context.__aenter__.side_effect = [
        response_429,
        response_429,
        response_429,
        response_429,
    ]
    with patch("asyncio.sleep", new_callable=AsyncMock), pytest.raises(RateLimitError):
            await call_riot_api(mock_session, "htpps://fakeurl.com", {})
    assert mock_session.get.call_count == 3
