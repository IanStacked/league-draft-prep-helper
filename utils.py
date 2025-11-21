import requests
from collections import Counter

def call_riot_api(api_url, headers):
    try:
        # Make the GET request with timeout
        response = requests.get(api_url, headers=headers, timeout=10)  # 10 seconds timeout
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            return data
        else:
            # Print an error message
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    
def get_puuid(game_name, tag_line, riot_api_key):
    api_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {
        "X-Riot-Token": riot_api_key,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0"
    }
    data = call_riot_api(api_url, headers)
    puuid = data.get('puuid')
    return puuid

def get_recent_matches(puuid, riot_api_key):
    api_url = f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&count=50"
    headers = {
        "X-Riot-Token": riot_api_key,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0"
    }
    match_ids = call_riot_api(api_url, headers)
    return match_ids
    
def get_match_details(match_id, riot_api_key):
    api_url = f"https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {
        "X-Riot-Token": riot_api_key,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0"
    }
    match_details = call_riot_api(api_url, headers)
    return match_details

def extract_player_champ_info(match_details, puuid):
    participants = match_details.get('info', {}).get('participants', [])
    for participant in participants:
        if participant.get('puuid') == puuid:
            return participant.get('championName')
    return None

def get_player_mastery(puuid, riot_api_key):
    api_url = f"https://na1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count=15"
    headers = {
        "X-Riot-Token": riot_api_key,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0"
    }
    mastery_info = call_riot_api(api_url, headers)
    return mastery_info
    
def collect_league_data(RIOT_API_KEY, game_name, tag_line):
    player_info = []
    puuid = get_puuid(game_name, tag_line, RIOT_API_KEY)
    recent_matches = get_recent_matches(puuid, RIOT_API_KEY)
    #mastery_info = get_player_mastery(puuid, RIOT_API_KEY)
    champions_played = []
    for match in recent_matches:
        champions_played.append(extract_player_champ_info(get_match_details(match,RIOT_API_KEY), puuid))
    champion_counts = Counter(champions_played)
    sorted_champions_played_counts = champion_counts.most_common()
    sorted_champions_played = [champion for champion, count in sorted_champions_played_counts]
    player_info.append({
        "game_name": game_name,
        "sorted_champions_played": sorted_champions_played
    })
    return player_info

def print_info_to_sheets(worksheet_string, sh, player_info, column_number=1):
    worksheet = sh.worksheet(worksheet_string)
    #set header
    worksheet.update_cell(1,column_number, player_info[0]["game_name"])
    #fill in data
    i = 2
    for champ in player_info[0]["sorted_champions_played"]:
        worksheet.update_cell(i, column_number, champ)
        i += 1