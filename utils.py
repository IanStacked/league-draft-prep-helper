import aiohttp
import asyncio
from collections import Counter

# Custom Exceptions
class RiotAPIError(Exception):
    #General RIOTAPI Error
    pass

class UserNotFound(RiotAPIError):
    #RIOT ID does not exist
    pass

class RateLimitError(RiotAPIError):
    #Rate Limit hit
    pass

# Core API Function

async def call_riot_api(session, url, headers, retries=3):
    for attempt in range(retries):
        try:
            async with session.get(url, headers=headers) as response:
                #Success
                if response.status == 200:
                    return await response.json()
                #Rate Limit Hit
                elif response.status == 429:
                    retry_after = int(response.headers.get("Retry-After",1))
                    print(f"⚠️ Rate Limit Hit! Sleeping for {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    continue
                #Other errors - dont retry
                elif response.status == 404:
                    # 404 usually means data/user not found
                    return None 
                elif response.status == 403:
                    raise RiotAPIError("Riot API Key is invalid or expired.")
                else:
                    raise RiotAPIError(f"Riot API Error {response.status}: {url}")
        except aiohttp.ClientError as e:
            raise RiotAPIError(f"Network Connection Failed: {e}")
    raise RateLimitError("Max retries exceeded for Riot API.")
    
# Specific Data Fetchers

async def get_puuid(session, game_name, tag_line, RIOT_API_KEY):
    api_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {
        "X-Riot-Token": RIOT_API_KEY,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0"
    }
    data = await call_riot_api(session, api_url, headers)
    if data is None:
        raise UserNotFound(f"User {game_name}#{tag_line} not found.")
    return data.get("puuid")

async def get_ranked_info(session, puuid, RIOT_API_KEY):
    # League-V4 MUST use a specific region like 'na1', 'euw1', 'kr'
    api_url = f"https://na1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    headers = {
        "X-Riot-Token": RIOT_API_KEY,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0"
    }
    data = await call_riot_api(session, api_url, headers)
    if data is None:
        raise UserNotFound(f"User with puuid: {puuid} not found.")
    soloq = None
    for entry in data:
        if entry.get("queueType") == "RANKED_SOLO_5x5":
            soloq = entry
            break
    if soloq:
        return {
        "tier": soloq.get("tier"),
        "rank": soloq.get("rank"),
        "LP": soloq.get("leaguePoints")
        }
    else:
        return {
        "tier": "",
        "rank": "Unranked",
        "LP": 0
        }

# def get_puuid(game_name, tag_line, riot_api_key):
#     api_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
#     headers = {
#         "X-Riot-Token": riot_api_key,
#         "Accept": "application/json",
#         "User-Agent": "LeagueHelperApp/1.0"
#     }
#     data = call_riot_api(api_url, headers)
#     puuid = data.get('puuid')
#     return puuid

# def get_recent_matches(puuid, riot_api_key):
#     api_url = f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&count=50"
#     headers = {
#         "X-Riot-Token": riot_api_key,
#         "Accept": "application/json",
#         "User-Agent": "LeagueHelperApp/1.0"
#     }
#     match_ids = call_riot_api(api_url, headers)
#     return match_ids
    
# def get_match_details(match_id, riot_api_key):
#     api_url = f"https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}"
#     headers = {
#         "X-Riot-Token": riot_api_key,
#         "Accept": "application/json",
#         "User-Agent": "LeagueHelperApp/1.0"
#     }
#     match_details = call_riot_api(api_url, headers)
#     return match_details

# def extract_player_champ_info(match_details, puuid):
#     participants = match_details.get('info', {}).get('participants', [])
#     for participant in participants:
#         if participant.get('puuid') == puuid:
#             return participant.get('championName')
#     return None

# def get_player_mastery(puuid, riot_api_key):
#     api_url = f"https://na1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count=15"
#     headers = {
#         "X-Riot-Token": riot_api_key,
#         "Accept": "application/json",
#         "User-Agent": "LeagueHelperApp/1.0"
#     }
#     mastery_info = call_riot_api(api_url, headers)
#     return mastery_info
    
# def collect_league_data(RIOT_API_KEY, game_name, tag_line):
#     player_info = []
#     puuid = get_puuid(game_name, tag_line, RIOT_API_KEY)
#     recent_matches = get_recent_matches(puuid, RIOT_API_KEY)
#     #mastery_info = get_player_mastery(puuid, RIOT_API_KEY)
#     champions_played = []
#     for match in recent_matches:
#         champions_played.append(extract_player_champ_info(get_match_details(match,RIOT_API_KEY), puuid))
#     champion_counts = Counter(champions_played)
#     sorted_champions_played_counts = champion_counts.most_common()
#     sorted_champions_played = [champion for champion, count in sorted_champions_played_counts]
#     player_info.append({
#         "game_name": game_name,
#         "sorted_champions_played": sorted_champions_played
#     })
#     return player_info

    worksheet = sh.worksheet(worksheet_string)
    #set header
    worksheet.update_cell(1,column_number, player_info[0]["game_name"])
    #fill in data
    i = 2
    for champ in player_info[0]["sorted_champions_played"]:
        worksheet.update_cell(i, column_number, champ)
        i += 1