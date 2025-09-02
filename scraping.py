#
# Program to scrape football data form FBREF
# 
# Written by: Ivan Lun Hui Chen (ichen9380@gmail.com)
# On: 2025/09/02
#-------------------------------------------------------------------------------
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import pandas as pd
from io import StringIO
import numpy as np
from datetime import datetime
import re, os

# setting up chrome driver to load js
driver = webdriver.Chrome()

def get_current_year():
    current_date = datetime.now()
    current_year = current_date.year
    return current_year

# Total number of years of data wanted
YEAR_DIFF = 4

CSV_FILE = 'matches.csv'

def getShootingStats(team_urls, year, all_matches):
    for team_url in team_urls:
        team_name = team_url.split('/')[-1].replace("-Stats", "").replace("-", " ")
        # getting all competition stats for the team instead of just its league
        team_url = re.sub(r'(/[^/]+)$',r'/all_comps\1-All-Competitions', team_url)
        # reading each team
        driver.get(team_url)
        time.sleep(3)
        page_source = driver.page_source

        # converting to pandas dataframe
        matches = pd.read_html(StringIO(page_source), match='Scores & Fixtures')[0]

        # getting the shooting stats
        soup = BeautifulSoup(page_source, features='html.parser')
        a_tags = soup.find_all('a')
        links = [a.get('href') for a in a_tags]
        shooting_links = [l for l in links if l and 'all_comps/shooting/' in l]
        driver.get(f'https://fbref.com{shooting_links[0]}')
        time.sleep(3)
        page_source = driver.page_source
        shooting = pd.read_html(StringIO(page_source), match='Shooting')[0]

        # getting the miscellaneous stats
        misc_links = [l for l in links if l and 'all_comps/misc/' in l]
        driver.get(f'https://fbref.com{misc_links[0]}')
        time.sleep(3)
        page_source = driver.page_source
        misc = pd.read_html(StringIO(page_source), match='Miscellaneous Stats')[0]

        # getting the goal and shot creation stats
        gca_links = [l for l in links if l and 'all_comps/gca/' in l]
        driver.get(f'https://fbref.com{gca_links[0]}')
        time.sleep(3)
        page_source = driver.page_source
        gca = pd.read_html(StringIO(page_source), match='Miscellaneous Stats')[0]

        # dropping the first level of column labels
        shooting.columns = shooting.columns.droplevel()
        misc.columns = misc.columns.droplevel()
        gca.columns = gca.columns.droplevel()

        try:
            team_data = matches.merge(shooting[['Date', 'Sh', 'SoT', 'Dist',
                                                'FK', 'PK', 'PKatt']], left_on='Date')
            team_data = matches.merge(misc[['Date', 'CrdY', 'CrdR', '2CrdY',
                                            'Fls', 'Fld', 'Off', 'Crs', 'Int',
                                            'TklW', 'Won%']], left_on='Date')
            team_data = matches.merge(gca[['SCA', 'GCA']], left_on='Date')
        except ValueError:
            continue

        # team_data = team_data[team_data['Comp'] == 'Premier League']
        team_data['Season'] = year
        team_data['Team'] = team_name
        all_matches.append(team_data)
        # separating our requests so that we don't flood the website
        time.sleep(1)

    return all_matches

def getStats(current_data_year=0):
    end_year = get_current_year()
    start_year = max(end_year - YEAR_DIFF, current_data_year)
    years = np.arange(end_year, start_year, -1)

    # if the current data is up to the current year, then only update the 
    # current year's data
    if len(years) == 0:
        years = [end_year]
    all_matches = []
    
    # URL of the webpage that we are scraping the data from
    info_url = 'https://fbref.com/en/comps/9/Premier-League-Stats'

    for year in years:
        # getting the data from the url
        driver.get(info_url)
        time.sleep(3)
        page_source = driver.page_source

        # using BeautifulSoup to parse the data
        soup = BeautifulSoup(page_source, features='html.parser')

        # getting the ending year of the season
        title = soup.select('h1')[0]
        title_match = re.search(r'([0-9]{4})-([0-9]{4})', str(title))
        year = title_match.group(2)

        # selecting the table using css selector
        standings_table = soup.select('table.stats_table')[0]

        # selecting all the a tags which are the teams
        a_tags = standings_table.find_all('a')

        # getting the links
        links = [l.get('href') for l in a_tags]
        links = [l for l in links if '/squads/' in l]
        team_urls = [f'https://fbref.com{l}' for l in links]

        previous_season = soup.select('a.prev')[0].get('href')
        info_url = f"https://fbref.com{previous_season}"

        all_matches = getShootingStats(team_urls, year, all_matches)

    return all_matches

# setting up path to csv and read csv file
csv_path = os.path.join(os.getcwd(), CSV_FILE)

# reading from csv to get the season needed to be updated, else scrape all seasons
# wanted 
all_matches =[]
if os.path.exists(csv_path):
    all_matches = pd.read_csv(CSV_FILE, index_col=0).sort_values('Date', ascending=False)
    current_data_year = all_matches.iloc[0]['Season']
    new_matches = getStats(current_data_year)
else:
    new_matches = getStats()

new_matches = pd.concat(new_matches)

# only adding the matches that are not already in the csv file
unique_keys = ['Date', 'Team', 'Opponent']
mask = ~new_matches.set_index(unique_keys).index.isin(all_matches.set_index(unique_keys).index)
new_unique_matches = new_matches[mask]

match_df = pd.concat([new_unique_matches, all_matches])

match_df.to_csv('matches.csv')