import requests
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import pandas as pd
from io import StringIO

# setting up chrome driver to load js
driver = webdriver.Chrome()

# URL of the webpage that we are scraping the data from
INFO_URL = 'https://fbref.com/en/comps/9/Premier-League-Stats'

# getting the data from the url
driver.get(INFO_URL)

time.sleep(5)

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

# reading first team
driver.get(team_urls[0])
time.sleep(5)
page_source = driver.page_source

# converting to pandas dataframe
matches = pd.read_html(StringIO(page_source), match='Scores & Fixtures')

print(matches[0])