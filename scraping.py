import requests
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import pandas as pd
from io import StringIO
import numpy as np

# setting up chrome driver to load js
driver = webdriver.Chrome()

START_YEAR = 2022
END_YEAR = 2025

def getShootingStats(team_urls, year, all_matches):
    for team_url in team_urls:
        team_name = team_url.split('/')[-1].replace("-Stats", "").replace("-", " ")
        # reading each team
        driver.get(team_url)
        time.sleep(3)
        page_source = driver.page_source

        # converting to pandas dataframe
        matches = pd.read_html(StringIO(page_source), match='Scores & Fixtures')[0]

        # getting the shooting stats
        soup = BeautifulSoup(page_source, features='html.parser')
        links = soup.find_all('a')
        links = [l.get('href') for l in links]
        links = [l for l in links if l and 'all_comps/shooting/' in l]
        driver.get(f'https://fbref.com{links[0]}')
        time.sleep(3)
        page_source = driver.page_source
        shooting = pd.read_html(StringIO(page_source), match='Shooting')[0]

        # dropping the first level of column labels
        shooting.columns = shooting.columns.droplevel()

        try:
            team_data = matches.merge(shooting[['Date', 'Sh', 'SoT', 'Dist', 'FK', 'PK', 'PKatt']], on='Date')
        except ValueError:
            continue

        team_data = team_data[team_data['Comp'] == 'Premier League']
        team_data['Season'] = year
        team_data['Team'] = team_name
        all_matches.append(team_data)
        # separating our requests so that we don't flood the website
        time.sleep(1)

    return all_matches

def getStats():
    years = np.arange(END_YEAR, START_YEAR, -1)
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

all_matches = []
all_matches = getStats()
match_df = pd.concat(all_matches)

match_df.to_csv('matches.csv')