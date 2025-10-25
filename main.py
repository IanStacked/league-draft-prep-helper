import os
import requests
from dotenv import load_dotenv

def get_puuid(game_name, tag_line, riot_api_key):
    api_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {
        "X-Riot-Token": riot_api_key,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0"
    }
    try:
        # Make the GET request with timeout
        response = requests.get(api_url, headers=headers, timeout=10)  # 10 seconds timeout
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            puuid = data.get('puuid')
            return puuid
        else:
            # Print an error message
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    
def get_recent_matches(puuid, riot_api_key):
    api_url = f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&count=50"
    headers = {
        "X-Riot-Token": riot_api_key,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0"
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            match_ids = response.json()
            return match_ids
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    
def get_match_details(match_id, riot_api_key):
    api_url = f"https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {
        "X-Riot-Token": riot_api_key,
        "Accept": "application/json",
        "User-Agent": "LeagueHelperApp/1.0"
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            match_details = response.json()
            return match_details
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    
def main():
    load_dotenv()
    RIOT_API_KEY = os.getenv("RIOT_API_KEY")
    GOOGLE_SHEETS_API_KEY = os.getenv("GOOGLE_SHEETS_API_KEY")

    print("Please input player information, format example: Game Name: frenzy, Tag Line: aja, for riotid frenzy#aja")
    game_name = input("Game Name: ",)
    tag_line = input("Tag Line: ",)
    puuid = get_puuid(game_name, tag_line, RIOT_API_KEY)
    recent_matches = get_recent_matches(puuid, RIOT_API_KEY)
    # only testing getting match details for the first recent match, can just loop over recent_matches when needed
    match_details = get_match_details(recent_matches[0], RIOT_API_KEY)
    print(f"PUUID: {puuid}")
    print(f"Recent Matches: {recent_matches}")
    print(f"Match Details for Match ID {recent_matches[0]}: {match_details}")

if __name__ == "__main__":
    main()
