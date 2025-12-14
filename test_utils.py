import pytest

from utils import parse_riot_id

# Tests for Helper Functions

def test_parse_riot_id_valid():
    assert parse_riot_id("Ninja#TAG") == ("Ninja","tag") # capitalized tag
    assert parse_riot_id("Ninja#tag") == ("Ninja","tag") # lowercase tag
    assert parse_riot_id("NiNJa#TaG") == ("NiNJa", "tag") # random caps

def test_parse_riot_id_invalid():
    assert parse_riot_id("NinjaTag") is None # no hashtag
    assert parse_riot_id("Ninja#") is None # no tag
    assert parse_riot_id("#tag") is None # no username