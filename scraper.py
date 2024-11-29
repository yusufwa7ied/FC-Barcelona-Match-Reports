import json
import time
import re
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import os
from utilities import preprocess_events, preprocess_data, convert_to_json

# Load environment variables from .env file
load_dotenv()

# Database configuration
MONGO_URI = f"mongodb+srv://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_CLUSTER')}.mongodb.net/{os.getenv('DB_NAME')}?retryWrites=true&w=majority"
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
    match_ids = set(item['_id'] for item in db.matches.find({}, {'_id': 1}))
    print("Existing match IDs in the database:", match_ids)
    return match_ids

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
        'date': datetime.strptime(matchdict.get('startTime'), "%Y-%m-%dT%H:%M:%S"),
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
            'competition': competition,
            'match_id': match_id
        }
        for key, value in event.items():
            event_info[key] = value
        events_data.append(event_info)
    
    
    matches_df, teams_df, players_df, events_df = preprocess_data(match_info, teams_data, players_data, events_data)
    return matches_df, teams_df, players_df, events_df




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
            matches_df, teams_df, players_df, events_df = scrape_match_data(driver, match_id, url, competition)

            # Add scraped data to respective lists
            if not matches_df.empty:
                all_matches.extend(matches_df.to_dict(orient='records'))
            if not teams_df.empty:
                all_teams.extend(teams_df.to_dict(orient='records'))
            if not players_df.empty:
                all_players.extend(players_df.to_dict(orient='records'))
            if not events_df.empty:
                all_events.extend(events_df.to_dict(orient='records'))
            
            time.sleep(INTERVAL_SECONDS)  # Pause to respect site requests
            
            
    # Preprocess data
    if all_matches or all_teams or all_players or all_events:
        # Preprocess the collected data
        matches_df, teams_df, players_df, events_df = preprocess_data(all_matches, all_teams, all_players, all_events)
        
        # Convert to JSON-compatible format for MongoDB
        matches_data, teams_data, players_data, events_data = convert_to_json(matches_df, teams_df, players_df, events_df)
        
        # Insert preprocessed data into MongoDB
        if matches_data:
            db.matches.insert_many(matches_data)
        if teams_data:
            for team in teams_data:
                db.teams.update_one(
                    {"_id": team["_id"]},  # Match by team ID
                    {"$set": team},        # Update the document
                    upsert=True            # Insert if it doesn't exist
                )
            #db.teams.insert_many(teams_data)
        if players_data:
            db.players.insert_many(players_data)
        if events_data:
            db.events.insert_many(events_data)


    print("New data successfully inserted.")
    client.close()
    driver.quit()

if __name__ == "__main__":
    main()