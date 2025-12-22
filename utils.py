import asyncio

import aiohttp

from logger_config import logger

# Custom Exceptions


class RiotAPIError(Exception):
    # General RIOTAPI Error
    pass


class UserNotFoundError(RiotAPIError):
    # RIOT ID does not exist
    pass


class RateLimitError(RiotAPIError):
    # Rate Limit hit
    pass


# Core API Function


async def call_riot_api(session, url, headers, retries=3):
    for _attempt in range(retries):
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 1))
                    logger.warning(
                        f"⚠️ Rate Limit Hit! Sleeping for {retry_after} seconds...",
                    )
                    await asyncio.sleep(retry_after)
                    continue
                # other errors - dont retry
                elif response.status == 404:
                    return None
                elif response.status == 403:
                    raise RiotAPIError("Riot API Key is invalid or expired.")
                else:
                    raise RiotAPIError(f"Riot API Error {response.status}: {url}")
        except aiohttp.ClientError as e:
            raise RiotAPIError("Network Connection Failed") from e
    raise RateLimitError("Max retries exceeded for Riot API.")


# Specific Data Fetchers


async def get_recent_match_info(session, puuid, riot_api_key):
    api_url = f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&count=1"
    headers = {
        "X-Riot-Token": riot_api_key,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0",
    }
    match_id = await call_riot_api(session, api_url, headers)
    api_url = f"https://americas.api.riotgames.com/lol/match/v5/matches/{match_id[0]}"
    match_info = await call_riot_api(session, api_url, headers)
    return match_info


async def get_puuid(session, game_name, tag_line, riot_api_key):
    api_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {
        "X-Riot-Token": riot_api_key,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0",
    }
    data = await call_riot_api(session, api_url, headers)
    if data is None:
        raise UserNotFoundError(f"User {game_name}#{tag_line} not found.")
    return data.get("puuid")


async def get_ranked_info(session, puuid, riot_api_key):
    # currently this api call will only work for NA users
    api_url = f"https://na1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    headers = {
        "X-Riot-Token": riot_api_key,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0",
    }
    data = await call_riot_api(session, api_url, headers)
    if data is None:
        raise UserNotFoundError(f"User with puuid: {puuid} not found.")
    soloq = None
    for entry in data:
        if entry.get("queueType") == "RANKED_SOLO_5x5":
            soloq = entry
            break
    if soloq:
        return {
            "tier": soloq.get("tier"),
            "rank": soloq.get("rank"),
            "LP": soloq.get("leaguePoints"),
        }
    else:
        return {"tier": "UNRANKED", "rank": "", "LP": 0}


# Helper Functions


def extract_match_info(match_dto, puuid):
    if not match_dto or "info" not in match_dto:
        return None
    participants = match_dto["info"].get("participants", [])
    for p in participants:
        if p.get("puuid") == puuid:
            return {
                "champion": p.get("championName"),
                "kda_formatted": f"{p.get('kills')}/{p.get('deaths')}/{p.get('assists')}",  # noqa: E501
            }
    return None


def parse_riot_id(unclean_riot_id):
    clean_riot_id = unclean_riot_id.strip()
    if "#" not in clean_riot_id:
        return None
    parts = clean_riot_id.split("#", 1)
    username = parts[0]
    tagline = parts[1]
    if not username or not tagline:
        return None
    # Taglines are case-insensitive. Lowercasing ensures that
    # identical RiotIDs are handled consistently
    return (username, tagline.lower())
