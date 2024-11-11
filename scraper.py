import json
import time
import re
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Database configuration
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
DB_NAME = "fcb2425"
INTERVAL_SECONDS = 2  # Delay between requests
BASE_URL = 'https://www.whoscored.com/Teams/65/Fixtures/Spain-Barcelona'

def initialize_driver():
    driver = webdriver.Chrome()
    driver.get(BASE_URL)
    time.sleep(3)
    return driver

def extract_match_urls(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    all_urls = soup.select('a[href*="\/Live\/"]')
    all_urls = list(set(['https://www.whoscored.com' + x.attrs['href'] for x in all_urls]))
    laliga_urls = [url for url in all_urls if 'LaLiga' in url]
    champions_league_urls = [url for url in all_urls if 'Champions-League' in url]
    return laliga_urls, champions_league_urls

def sum_stats(stats_dict, exclude_keys=None):
    exclude_keys = exclude_keys or []
    return sum(value for key, value in stats_dict.items() if key not in exclude_keys)

def get_existing_match_ids(db):
    return set(item['_id'] for item in db.matches.find({}, {'_id': 1}))

def scrape_match_data(driver, match_id, url, competition):
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    element = soup.select_one('script:-soup-contains("matchCentreData")')
    if element is None:
        print(f"No matchCentreData found for URL: {url}")
        return None

    matchdict = json.loads(element.text.split("matchCentreData: ")[1].split(',\n')[0])
    
    match_info = {
        '_id': match_id,
        'competition': competition,
        'date': matchdict.get('startTime'),
        'home_team_id': matchdict['home']['teamId'],
        'away_team_id': matchdict['away']['teamId'],
        'home_team_name': matchdict['home']['name'],
        'away_team_name': matchdict['away']['name'],
        'home_score_fulltime': matchdict['home']['scores'].get('fulltime', 0),
        'away_score_fulltime': matchdict['away']['scores'].get('fulltime', 0),
        'home_shots_total': sum_stats(matchdict['home']['stats'].get('shotsTotal', {})),
        'home_shots_on_target': sum_stats(matchdict['home']['stats'].get('shotsOnTarget', {})),
        'home_possession': sum_stats(matchdict['home']['stats'].get('possession', {})),
        'home_passes_total': sum_stats(matchdict['home']['stats'].get('passesTotal', {})),
        'home_pass_completion': sum_stats(matchdict['home']['stats'].get('passesAccurate', 0)),
        'home_fouls_committed': sum_stats(matchdict['home']['stats'].get('foulsCommited', {})),
        'home_corners': sum_stats(matchdict['home']['stats'].get('cornersTotal', {})),
        'home_offsides_caught': sum_stats(matchdict['home']['stats'].get('offsidesCaught', {})),
        'away_shots_total': sum_stats(matchdict['away']['stats'].get('shotsTotal', {})),
        'away_shots_on_target': sum_stats(matchdict['away']['stats'].get('shotsOnTarget', {})),
        'away_possession': sum_stats(matchdict['away']['stats'].get('possession', {})),
        'away_passes_total': sum_stats(matchdict['away']['stats'].get('passesTotal', {})),
        'away_pass_completion': sum_stats(matchdict['away']['stats'].get('passesAccurate', 0)),
        'away_fouls_committed': sum_stats(matchdict['away']['stats'].get('foulsCommited', {})),
        'away_corners': sum_stats(matchdict['away']['stats'].get('cornersTotal', {})),
        'away_offsides_caught': sum_stats(matchdict['away']['stats'].get('offsidesCaught', {}))
    }

    teams_data = []
    for side in ['home', 'away']:
        team = matchdict[side]
        teams_data.append({
            '_id': team['teamId'],
            'name': team['name'],
            'country_name': team['countryName'],
            'manager_name': team.get('managerName', 'Unknown'),
            'competition': competition
        })

    players_data = []
    for side in ['home', 'away']:
        team = matchdict[side]
        for player in team['players']:
            players_data.append({
                '_id': f"{player['playerId']}_{match_id}",
                'player_id': player['playerId'],
                'name': player['name'],
                'shirt_no': player['shirtNo'],
                'position': player['position'],
                'age': player.get('age', 'Unknown'),
                'team_id': team['teamId'],
                'stats': player.get('stats', {}),
                'competition': competition,
                'match_id': match_id
            })

    events_data = []
    for event in matchdict['events']:
        event_info = {
            '_id': f"{match_id}_{event['eventId']}_{event['minute']}_{event.get('playerId', '')}",
            'competition': competition,
            'match_id': match_id,
            'event_type_id': event.get('eventId'),
            'minute': event.get('minute'),
            'second': event.get('second', 0),
            'team_id': event.get('teamId'),
            'player_id': event.get('playerId'),
            'type': event.get('type', {}).get('displayName'),
            'outcomeType': event.get('outcomeType', {}).get('displayName'),
            'x': event.get('x'),
            'y': event.get('y'),
            'end_x': event.get('endX', 0),
            'end_y': event.get('endY', 0)
        }
        events_data.append(event_info)

    return match_info, teams_data, players_data, events_data

def main():
    # MongoDB setup
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Get existing match IDs to avoid re-scraping
    existing_match_ids = get_existing_match_ids(db)
    
    # Initialize WebDriver and scrape URLs
    driver = initialize_driver()
    laliga_urls, champions_league_urls = extract_match_urls(driver)
    
    # Initialize lists to hold new data
    all_matches = []
    all_teams = []
    all_players = []
    all_events = []
    
    # Loop over URLs for each competition
    for competition, urls in [("La Liga", laliga_urls), ("Champions League", champions_league_urls)]:
        for url in urls:
            # Extract match ID
            match_id = int(re.search(r"Matches/(\d+)/", url).group(1))
            
            # Skip if match already exists in the database
            if match_id in existing_match_ids:
                print(f"Match {match_id} already exists. Skipping...")
                continue
            
            # Scrape match data
            print(f"Scraping new match: {match_id} ({competition})")
            match_info, teams_data, players_data, events_data = scrape_match_data(driver, match_id, url, competition)
            
            if match_info:
                all_matches.append(match_info)
                all_teams.extend(teams_data)
                all_players.extend(players_data)
                all_events.extend(events_data)
            
            time.sleep(INTERVAL_SECONDS)  # Pause to respect site requests
    
    # Insert only new data
    if all_matches:
        db.matches.insert_many(all_matches)
    if all_teams:
        db.teams.insert_many(all_teams)
    if all_players:
        db.players.insert_many(all_players)
    if all_events:
        db.events.insert_many(all_events)
    
    print("New data successfully inserted.")
    client.close()
    driver.quit()

if __name__ == "__main__":
    main()