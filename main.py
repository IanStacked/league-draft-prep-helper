from bot import bot_startup

def main():

    bot_startup()
    #google sheets verification
    # gc = gspread.service_account(filename='credentials.json')
    # try:
    #     #this key determines which sheet is opened
    #     sh = gc.open_by_key("1wp9h_LorMKCMWHLCfBOjq8WlZUuw2mgYlUqnJv7GeXY")
    # except gspread.SpreadsheetNotFound:
    #     print("Error: Spreadsheet not found")
    #     exit(1)
    #list of riot IDs to process
    # riot_ids = [
    #     ("frenzy","aja"), 
    #     ("Doug105","0000"),
    #     ("Stickb0y99","SM99"),
    #     ("Nightske","#NA1"),
    #     ("aspect of banana","#int")
    #     ]
    
    #processing each riot ID
    # i = 1
    # for riot_id in riot_ids:
    #     player_info = collect_league_data(RIOT_API_KEY, riot_id[0], riot_id[1])
    #     print_info_to_sheets("Sheet5", sh, player_info, i)
    #     i += 1
    #     time.sleep(130)  # seconds


if __name__ == "__main__":
    main()
