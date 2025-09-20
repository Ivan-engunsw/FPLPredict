#
# Program to scrape football data form FBREF
# 
# Written by: Ivan Lun Hui Chen (ichen9380@gmail.com)
# On: 2025/09/02
#-------------------------------------------------------------------------------
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
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

LEAGUE = 'La Liga'
# Total number of years of data wanted
YEAR_DIFF = 4

# CSV file names
MATCHES_CSV_FILE = 'matches.csv'
HISTORY_CSV_FILE = 'history.csv'
NEXT_MATCHES_CSV_FILE = 'next_matches.csv'

def read_data_with_retry(url, id_match, table_match, retries=3, delay=2):
    for attempt in range(retries):
        # getting the data from the url
        driver.get(url)
        # wait until table exists in DOM
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, id_match))
            )
            page_source = driver.page_source
            time.sleep(2)
            return (pd.read_html(StringIO(page_source), match=table_match)[0], page_source)
        except TimeoutException:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                print(url)

def get_matches_stats(team_urls, year, all_matches, next_matches,
                      history_matches, head_to_head_urls):
    for team_url in team_urls:
        team_name_with_dash = team_url.split('/')[-1].replace('-Stats', '')
        team_name = team_name_with_dash.replace('-', ' ')
        team_id_match = re.search('/squads/[^/]+', team_url)
        team_id = team_id_match.group(0).split('/')[-1]
        # getting all competition stats for the team instead of just its league
        team_url = re.sub(r'(/[^/]+)$',r'/all_comps\1-All-Competitions', team_url)

        # converting to pandas dataframe
        (matches, page_source) = read_data_with_retry(team_url, 'matchlogs_for', table_match='Scores & Fixtures')
        matches['Season'] = year
        matches['Team'] = team_name
        past_matches = matches[matches['Result'].notna()]
        next_match = matches[matches['Result'].isna()]
        
        # getting all the a tags with their links
        soup = BeautifulSoup(page_source, features='html.parser')
        a_tags = soup.find_all('a')
        links = [a.get('href') for a in a_tags]

        past_week_matches_csv_path = os.path.join(os.getcwd(), NEXT_MATCHES_CSV_FILE)
        if os.path.exists(past_week_matches_csv_path):
            try:
                past_week_matches_df = pd.read_csv(NEXT_MATCHES_CSV_FILE, index_col=0)
                past_week_teams = set(list(past_week_matches_df['Team']))
            except pd.errors.EmptyDataError:
                past_week_teams = set()
        else:
            past_week_teams = set()

        # getting all the td tags with opponents to get the history matches data
        td_tags = set(soup.find_all('td', {'class': 'left', 'data-stat': 'opponent'}))
        for td in td_tags:
            # getting the links and all the info required for the history url
            link = td.find('a').get('href')
            opp_name = link.split('/')[-1].replace('-Stats', '')
            opp_id_match = re.search('/squads/[^/]+', link)
            opp_id = opp_id_match.group(0).split('/')[-1]
            head_to_head_history_url = ('https://fbref.com/en/stathead/matchup/' + 
                                        f'teams/{team_id}/{opp_id}/{team_name_with_dash}' + 
                                        f'-vs-{opp_name}-History')

            # skip if the history already has been read before
            if head_to_head_history_url in head_to_head_urls:
                continue
            head_to_head_urls.add(head_to_head_history_url)
            
            if ((team_name in past_week_teams and opp_name.replace('-',' ') in past_week_teams)
                or len(past_week_teams) == 0):
                try:
                    (hth_matches, page_source) = read_data_with_retry(head_to_head_history_url, 
                                                    'games_history_all',
                                                    table_match='Head-to-Head Matches')
                    # only reading matches that have already happened
                    hth_matches = hth_matches[hth_matches['Score'].notna()]
                    # only keeping rows with data and not labels
                    hth_matches = hth_matches[hth_matches['Date'] != 'Date']
                    hth_matches['Team'] = team_name
                    history_matches.append(hth_matches)
                except ValueError:
                    print(head_to_head_history_url)
                    continue

        # getting the shooting stats
        shooting_links = [l for l in links if l and 'all_comps/shooting/' in l]
        (shooting, page_source) = read_data_with_retry(f'https://fbref.com{shooting_links[0]}',
                                        'matchlogs_for',
                                        table_match='Shooting')

        # getting the miscellaneous stats
        misc_links = [l for l in links if l and 'all_comps/misc/' in l]
        (misc, page_source) = read_data_with_retry(f'https://fbref.com{misc_links[0]}',
                                    'matchlogs_for',
                                    table_match='Miscellaneous Stats')

        # getting the goal and shot creation stats
        gca_links = [l for l in links if l and 'all_comps/gca/' in l]
        (gca, page_source) = read_data_with_retry(f'https://fbref.com{gca_links[0]}',
                                    'matchlogs_for',
                                    table_match='Goal and Shot Creation')

        # dropping the first level of column labels
        shooting.columns = shooting.columns.droplevel()
        misc.columns = misc.columns.droplevel()
        gca.columns = gca.columns.droplevel()

        # try merging any additional data to the matches if it exists
        try:
            team_data = past_matches.merge(shooting[['Date', 'Sh', 'SoT', 'Dist',
                                                'FK', 'PK', 'PKatt']],
                                                on='Date', how='left')
            team_data = team_data.merge(misc[['Date', 'CrdY', 'CrdR', '2CrdY',
                                            'Fls', 'Fld', 'Off', 'Crs', 'Int',
                                            'TklW', 'Won%']],
                                            on='Date', how='left')
            team_data = team_data.merge(gca[['Date', 'SCA', 'GCA']],
                                      on='Date', how='left')
        except ValueError:
            continue

        # only keeping rows with data and not labels
        team_data = team_data[team_data['Date'] != 'Date']
        all_matches.append(team_data)
        if (not next_match.empty):
            next_match = next_match[next_match['Comp'] == LEAGUE]
            next_matches.append(pd.DataFrame([next_match.iloc[0]]))

        # separating our requests so that we don't flood the website
        time.sleep(1)

    return (all_matches, next_matches, history_matches)

def get_stats(current_data_year=0):
    end_year = get_current_year()
    start_year = max(end_year - YEAR_DIFF, current_data_year)
    years = np.arange(end_year, start_year, -1)

    # if the current data is up to the current year, then only update the 
    # current year's data
    if len(years) == 0:
        years = [end_year]
    past_matches, next_matches, history_matches = [], [], []

    head_to_head_urls = set()

    # URL of the webpage that we are scraping the data from
    if LEAGUE == 'Premier League':
        info_url = 'https://fbref.com/en/comps/9/Premier-League-Stats'
    elif LEAGUE == 'La Liga':
        info_url = 'https://fbref.com/en/comps/12/La-Liga-Stats'

    for year in years:
        retries = 3
        for attempt in range(retries):
            # getting the data from the url
            driver.get(info_url)
            # wait until table exists in DOM
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'stats_table'))
                )
                time.sleep(2)
                page_source = driver.page_source
                break
            except TimeoutException:
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    print(info_url)

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

        # setting up the url for previous season to be read next
        previous_season = soup.select('a.prev')[0].get('href')
        info_url = f'https://fbref.com{previous_season}'

        (past_matches, new_matches,
         history_matches) = get_matches_stats(team_urls, year, past_matches,
                                              next_matches, history_matches,
                                              head_to_head_urls)
    return (past_matches, new_matches, history_matches)

# setting up path to csv files and read them
matches_csv_path = os.path.join(os.getcwd(), MATCHES_CSV_FILE)
next_matches_csv_path = os.path.join(os.getcwd(), NEXT_MATCHES_CSV_FILE)
history_csv_path = os.path.join(os.getcwd(), HISTORY_CSV_FILE)

# reading from csv to get the season needed to be updated, else scrape all seasons
# wanted 
if (os.path.exists(matches_csv_path) and os.path.exists(next_matches_csv_path)
    and os.path.exists(history_csv_path)):
    try:
        # reading in the past matches data in the csv and adding new data
        csv_all_matches = pd.read_csv(MATCHES_CSV_FILE, index_col=0).sort_values('Date', ascending=False)
        current_data_year = csv_all_matches.iloc[0]['Season']
        (new_matches, next_new_matches, history_new_matches) = get_stats(current_data_year)
        if new_matches:
            new_matches = pd.concat(new_matches, ignore_index=True)
            next_new_matches = pd.concat(next_new_matches, ignore_index=True)
            # only adding the matches that are not already in the csv file
            unique_keys = ['Date', 'Team', 'Opponent']
            mask = ~new_matches.set_index(unique_keys).index.isin(csv_all_matches.set_index(unique_keys).index)
            new_unique_matches = new_matches[mask]

            new_dfs = [df for df in [new_unique_matches, csv_all_matches] if not df.empty]
            match_df = pd.concat(new_dfs, ignore_index=True)

            # reading in the next matches data in the csv and adding new data
            next_matches_df = pd.concat([next_new_matches], ignore_index=True)
            # converting data into csv
            match_df.to_csv(MATCHES_CSV_FILE)
            next_matches_df.to_csv(NEXT_MATCHES_CSV_FILE)

        if history_new_matches:
            history_new_matches = pd.concat(history_new_matches, ignore_index=True)
            # reading in the head-to-head matches data in the csv and adding new data
            csv_history_matches = pd.read_csv(HISTORY_CSV_FILE, index_col=0).sort_values('Date', ascending=False)

            history_new_matches['Match_key'] = history_new_matches.apply(
                lambda row: tuple(sorted([row['Home'], row['Away']])), axis=1)

            history_new_matches.drop_duplicates(subset=['Match_key', 'Date'], inplace=True)
            history_new_matches.drop(columns=['Match_key', 'Match Report'], inplace=True)

            # only adding the matches that are not already in the csv file
            unique_keys = ['Date', 'Home', 'Away', 'Comp']
            history_mask = ~history_new_matches.set_index(unique_keys).index.isin(csv_history_matches.set_index(unique_keys).index)
            history_new_unique_matches = history_new_matches[history_mask]

            new_dfs = [df for df in [history_new_unique_matches, csv_history_matches] if not df.empty]
            history_matches_df = pd.concat(new_dfs, ignore_index=True)
            history_matches_df.to_csv(HISTORY_CSV_FILE)
    except pd.errors.EmptyDataError:
        (new_matches, next_new_matches, history_new_matches) = get_stats()
        match_df = pd.concat(new_matches, ignore_index=True)
        next_matches_df = pd.concat(next_new_matches, ignore_index=True)
        history_matches_df = pd.concat(history_new_matches, ignore_index=True)
        # converting data into csv
        match_df.to_csv(MATCHES_CSV_FILE)
        next_matches_df.to_csv(NEXT_MATCHES_CSV_FILE)
        history_matches_df.to_csv(HISTORY_CSV_FILE)
else:
    (new_matches, next_new_matches, history_new_matches) = get_stats()
    match_df = pd.concat(new_matches, ignore_index=True)
    next_matches_df = pd.concat(next_new_matches, ignore_index=True)
    history_matches_df = pd.concat(history_new_matches, ignore_index=True)
    # converting data into csv
    match_df.to_csv(MATCHES_CSV_FILE)
    next_matches_df.to_csv(NEXT_MATCHES_CSV_FILE)
    history_matches_df.to_csv(HISTORY_CSV_FILE)