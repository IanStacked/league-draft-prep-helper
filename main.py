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
    
def main():
    load_dotenv()
    RIOT_API_KEY = os.getenv("RIOT_API_KEY")
    GOOGLE_SHEETS_API_KEY = os.getenv("GOOGLE_SHEETS_API_KEY")

    print("Please input player information, format example: Game Name: frenzy, Tag Line: aja for riotid frenzy#aja")
    game_name = input("Game Name: ",)
    tag_line = input("Tag Line: ",)
    puuid = get_puuid(game_name, tag_line, RIOT_API_KEY)
    print(puuid)

if __name__ == "__main__":
    main()
