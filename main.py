import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    RIOT_API_KEY = os.getenv("RIOT_API_KEY")
    GOOGLE_SHEETS_API_KEY = os.getenv("GOOGLE_SHEETS_API_KEY")
    
    print("Hello from leaguehelper!")


if __name__ == "__main__":
    main()
