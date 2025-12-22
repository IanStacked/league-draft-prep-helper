import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from discord.ext import commands

# Prevents our tests from trying to start the real database when we import from bot.py
mock_database = MagicMock()
mock_database.database_startup.return_value = MagicMock()
mock_database.TRACKED_USERS_COLLECTION = "tracked_users"
sys.modules["database"] = mock_database
from bot import hello, track  # noqa: E402


@pytest.fixture
def mock_ctx():
    ctx = MagicMock(spec=commands.Context)
    ctx.send = AsyncMock()
    ctx.author.display_name = ""
    ctx.guild.id = 123456789
    ctx.author.id = 1
    return ctx


@pytest.fixture
def mock_db():
    with patch("bot.db") as mock_db_instance:
        collection_mock = MagicMock()
        document_mock = MagicMock()
        mock_db_instance.collection.return_value = collection_mock
        mock_db_instance.document.return_value = document_mock
        document_mock.set = MagicMock()
        yield mock_db_instance


@pytest.mark.asyncio
async def test_hello_success(mock_ctx):
    mock_ctx.author.display_name = "John"
    await hello(mock_ctx)
    mock_ctx.send.assert_called_with(f"Hello {mock_ctx.author.display_name}")


@pytest.mark.asyncio
async def test_track_success(mock_ctx, mock_db):
    fake_riot_id = "bob#boom"
    with patch("bot.get_puuid", new_callable=AsyncMock) as fake_get_puuid:
        fake_get_puuid.return_value = 12345
        with patch(
            "bot.get_ranked_info",
            new_callable=AsyncMock,
        ) as fake_get_ranked_info:
            fake_get_ranked_info.return_value = {"tier": "paper", "rank": "1", "LP": 10}
            await track(mock_ctx, riot_id=fake_riot_id)
            doc_mock = mock_db.collection.return_value.document.return_value
            doc_mock.set.assert_called_once()
            args, kwargs = doc_mock.set.call_args
            saved_data = args[0]
            assert saved_data["puuid"] == 12345
            assert saved_data["tier"] == "paper"
            assert saved_data["rank"] == "1"
            assert saved_data["LP"] == 10
            assert saved_data["server_info.123456789"]["added_by"] == 1
            assert kwargs.get("merge")
            mock_ctx.send.assert_called_with("bob#boom is now being tracked!")
