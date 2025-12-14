import pytest
from unittest.mock import AsyncMock, MagicMock

from utils import parse_riot_id, get_puuid, get_ranked_info
from utils import UserNotFound

# Tests for Helper Functions

def test_parse_riot_id_valid():
    assert parse_riot_id("Ninja#TAG") == ("Ninja","tag") # capitalized tag
    assert parse_riot_id("Ninja#tag") == ("Ninja","tag") # lowercase tag
    assert parse_riot_id("NiNJa#TaG") == ("NiNJa", "tag") # random caps

def test_parse_riot_id_invalid():
    assert parse_riot_id("NinjaTag") is None # no hashtag
    assert parse_riot_id("Ninja#") is None # no tag
    assert parse_riot_id("#tag") is None # no username

# Tests for API Functions

@pytest.fixture
def mock_session():
    session = MagicMock()
    context_manager = MagicMock()
    response = AsyncMock()
    response.status = 200
    response.json.return_value={}
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
    test_data = [{"queueType": "RANKED_FLEX_SR", "tier": "SILVER", "rank": "I", "leaguePoints": 10},
                 {"queueType": "RANKED_SOLO_5x5", "tier": "GOLD", "rank": "IV", "leaguePoints": 20}]
    mock_response = mock_session.get.return_value.__aenter__.return_value
    mock_response.json.return_value = test_data
    result = await get_ranked_info(mock_session, "puuid", "KEY")
    assert result["tier"] == "GOLD"
    assert result["rank"] == "IV"
    assert result["LP"] == 20

@pytest.mark.asyncio
async def test_get_ranked_info_unranked(mock_session):
    mock_response = mock_session.get.return_value.__aenter__.return_value
    mock_response.json.return_value = "" #not None, as that is what returned for invalid puuid
    result = await get_ranked_info(mock_session, "puuid", "KEY")
    assert result["tier"] == "UNRANKED"
    assert result["rank"] == ""
    assert result["LP"] == 0

@pytest.mark.asyncio
async def test_get_ranked_info_invalid_puuid(mock_session):
    mock_response = mock_session.get.return_value.__aenter__.return_value
    mock_response.status = 404
    mock_response.json.return_value = None
    with pytest.raises(UserNotFound) as exc_info:
        await get_ranked_info(mock_session, "puuid", "KEY")