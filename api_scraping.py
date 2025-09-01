import requests, os, json, time

COUNTRY = "England"
LEAGUE = "Premier League"
NUM_SEASONS_USED = 3
SLEEP_SECS = 6

# getting the api key
config_file_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_file_path) as config_file:
    config = json.load(config_file)
api_key = config["API_key"]

def make_request(url, params, num_retries=5, delay=1):
    for attempt in range(num_retries):
        headers = {"X-API-Key": api_key}

        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            return response
        else:
            print(f"Attempt {attempt} failed with status code {response.status_code}")
            time.sleep(SLEEP_SECS + delay)
            delay *= 2
    
    return None

# # getting the country code for the country of the league wanted
# url = "https://fbrapi.com/countries"
# params = {
#     "country": COUNTRY
# }

# response = make_requests(url, params)
# country_code = response.json()["country_code"]

# # pausing execution due to rate limiting according to api documentation
# time.sleep(SLEEP_SECS)

# # getting the country code for the country of the league wanted
# url = "https://fbrapi.com/leagues"
# params = {
#     "country_code": country_code
# }

# response = make_requests(url, params)
# # getting the list of different league types in the country
# league_types = response.json()["data"]

# # finding the league information about the desired league
# for league_type in league_types:
#     for league in league_type["leagues"]:
#         if league["competition_name"] == LEAGUE:
#             league_info = league

# league_id = league_info["league_id"]

# # pausing execution due to rate limiting according to api documentation
# time.sleep(SLEEP_SECS)

# league_id = 9
# # getting the seasons of the league wanted
# url = "https://fbrapi.com/league-seasons"
# params = {
#     "league_id": league_id
# }

# response = make_requests(url, params)
# # getting all seasons of the league
# seasons = response.json()["data"][0:NUM_SEASONS_USED]

# # # pausing execution due to rate limiting according to api documentation
# time.sleep(SLEEP_SECS)

# seasons_standings_string = ""
# teams = dict()

# # getting the league standings of the seasons wanted
# for season in seasons:
#     url = "https://fbrapi.com/league-standings"
#     params = {
#         "league_id": league_id,
#         # "season_id": season["season_id"]
#     }

#     response = make_request(url, params)
#     # getting all seasons of the league
#     print(response.headers)
#     standings = response.json()["standings"]
#     teams[standings["team_name"]] = standings["team_id"]
#     seasons_standings_string += standings

# print(seasons_standings_string)

# for team, team_id in teams.items():
#     url = "https://fbrapi.com/teams"
#     params = {
#         "league_id": 9,
#         "season_id": 
#     }
#     headers = {"X-API-Key": api_key}

#     response = requests.get(url, params=params, headers=headers)
#     # getting all seasons of the league
#     print(response.text)
    

