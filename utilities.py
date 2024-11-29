from PIL import Image, ImageOps
from datetime import datetime
import base64
from io import BytesIO
import pandas as pd


def format_team_name(name):
    return name.lower().replace(" ", "_")


def load_and_resize_logo(team_name, box_size=(150, 150)):
    logo_path = f"team_logos/{format_team_name(team_name)}_logo.png"
    logo = Image.open(logo_path).convert("RGBA")  # Convert to RGBA to handle transparency

    # Crop transparent padding around the image
    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)

    logo.thumbnail(box_size, Image.LANCZOS)
    
    # Convert image to Base64
    buffered = BytesIO()
    logo.save(buffered, format="PNG")
    encoded_logo = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    return encoded_logo


# Define individual functions for each DataFrame

def preprocess_matches(all_matches):
    if not isinstance(all_matches, list) or not all_matches:
        return pd.DataFrame(columns=['_id', 'date', 'home_score_fulltime', 'away_score_fulltime'])
    

    matches_df = pd.DataFrame(all_matches)
    
    # Convert 'date' column to datetime format
    matches_df['date'] = pd.to_datetime(matches_df['date'], errors='coerce')
    
    # Convert score columns to integers and handle missing values
    score_columns = ['home_score_fulltime', 'away_score_fulltime']
    matches_df[score_columns] = matches_df[score_columns].fillna(0).astype(int)
    
    # Handle other columns if necessary (e.g., fill NaNs for stats columns, convert types)
    stats_columns = [
        'home_shots_total', 'home_shots_on_target', 'home_possession', 'home_passes_total', 
        'home_pass_completion', 'home_fouls_committed', 'home_corners', 'home_offsides_caught', 
        'away_shots_total', 'away_shots_on_target', 'away_possession', 'away_passes_total', 
        'away_pass_completion', 'away_fouls_committed', 'away_corners', 'away_offsides_caught'
    ]
    matches_df[stats_columns] = matches_df[stats_columns].fillna(0).astype(float)
    
    return matches_df

def preprocess_teams(all_teams):
    teams_df = pd.DataFrame(all_teams).drop_duplicates(subset=['_id'])
    teams_df = teams_df[['_id', 'name', 'manager_name', 'competition']]
    teams_df['competition'] = teams_df['competition'].astype('category')
    return teams_df

def preprocess_players(all_player_stats):
    players_df = pd.DataFrame(all_player_stats)
    players_df = players_df[[
        '_id', 'name', 'shirt_no', 'position', 'age', 'team_id', 'stats', 'competition', 'match_id'
    ]]
    players_df['age'] = players_df['age'].fillna(0).astype(int)
    players_df['shirt_no'] = players_df['shirt_no'].astype(int)
    players_df['position'] = players_df['position'].astype('category')
    players_df['competition'] = players_df['competition'].astype('category')
    return players_df

def preprocess_events(all_events):
    events_df = pd.DataFrame(all_events)
    # Define the required columns with their default values
    required_columns = {
        'competition': None,
        'match_id': None,
        'id': None,
        'eventId': None,
        'minute': 0,
        'second': 0,
        'teamId': None,
        'period': None,
        'playerId': None,
        'type': None,
        'outcomeType': None,
        'x': 0.0,
        'y': 0.0,
        'endX': 0.0,
        'endY': 0.0,
        'goalMouthZ': 0.0,
        'goalMouthY': 0.0,
        'isTouch': False,
        'isShot': False,
        'isGoal': False,
        'cardType': None,
        'isOwnGoal': False
    }
    
    # Ensure all required columns exist in the DataFrame
    for col, default_value in required_columns.items():
        if col not in events_df:
            events_df[col] = default_value
    events_df = events_df.dropna(subset=['playerId'])
    
    
   # Extract display names for dictionary columns
    for col in ['period', 'type', 'outcomeType', 'cardType']:
        events_df[col] = events_df[col].apply(lambda x: x['displayName'] if isinstance(x, dict) else x)
        
    numeric_columns = ['minute', 'second', 'x', 'y', 'endX', 'endY', 'goalMouthZ', 'goalMouthY']
    for col in numeric_columns:
        events_df[col] = pd.to_numeric(events_df[col], errors='coerce').fillna(0).astype(float)
    
    # Convert boolean columns
    boolean_columns = ['isTouch', 'isShot', 'isGoal', 'isOwnGoal']
    for col in boolean_columns:
        events_df[col] = events_df[col].astype(bool)
    
    
    # Select and rename columns
    events_df = events_df[[
        'competition', 'match_id', 'id', 'eventId', 'minute', 'second', 'teamId', 'period',
        'playerId', 'type', 'outcomeType', 'x', 'y', 'endX', 'endY',
        'goalMouthZ', 'goalMouthY', 'isTouch', 'isShot', 'isGoal', 'cardType', 'isOwnGoal'
    ]]
    
    # Calculate total_seconds and sort
    events_df['total_seconds'] = events_df['minute'] * 60 + events_df['second']
    events_df = events_df.sort_values(by=['match_id', 'total_seconds'])
    
    # Assign passer and recipient
    events_df['passer'] = events_df.apply(lambda row: row['playerId'] if row['type'] == 'Pass' else None, axis=1)
    successful_passes = events_df[(events_df['type'] == 'Pass') & (events_df['outcomeType'] == 'Successful')].copy()
    successful_passes['recipient'] = successful_passes['playerId'].shift(-1)
    events_df = pd.merge(
        events_df,
        successful_passes[['id', 'total_seconds', 'type', 'recipient']],
        how='left',
        on=['id', 'total_seconds', 'type']
    )
    
    # Final adjustments
    if 'passer_x' in events_df.columns:
        events_df.rename(columns={'passer_x': 'passer'}, inplace=True)
        events_df['passer'] = events_df['passer'].astype(pd.Int64Dtype())
        events_df['recipient'] = events_df['recipient'].astype(pd.Int64Dtype())
        events_df.rename(columns={
        'id': 'event_id', 'eventId': 'event_type_id', 'teamId': 'team_id', 'playerId': 'player_id',
        'outcomeType': 'type_outcome', 'endX': 'end_x', 'endY': 'end_y',
        'goalMouthZ': 'goal_mouth_z', 'goalMouthY': 'goal_mouth_y', 'isTouch': 'is_touch',
        'isShot': 'is_shot', 'isGoal': 'is_goal', 'cardType': 'card_type', 'isOwnGoal': 'is_own_goal'
    }, inplace=True)
    return events_df

# Main processing function
def preprocess_data(all_matches, all_teams, all_player_stats, all_events):
    matches_df = preprocess_matches(all_matches)
    teams_df = preprocess_teams(all_teams)
    players_df = preprocess_players(all_player_stats)
    events_df = preprocess_events(all_events)
    # Rename columns to use as MongoDB _id
    #matches_df = matches_df.rename(columns={'match_id': '_id'})
    #teams_df = teams_df.rename(columns={'team_id': '_id'})
    #players_df['player_id'] = players_df.apply(lambda row: f"{row['player_id']}_{row['match_id']}", axis=1)
    #players_df = players_df.rename(columns={'player_id': '_id'})
    # Create a unique _id by combining match_id, event_type_id, total_seconds, and player_id
    #events_df['event_id'] = events_df.apply(lambda row: f"{row['match_id']}_{row['event_type_id']}_{row['total_seconds']}_{row['player_id']}", axis=1)
    #events_df = events_df.rename(columns={'event_id': '_id'})
    return matches_df, teams_df, players_df, events_df


# Function to convert DataFrames to JSON-like format with <NA> replaced by None for MongoDB
def convert_to_json(matches_df, teams_df, players_df, events_df):
    def safe_to_dict(df):
        if df.empty:
            return []
        return df.applymap(lambda x: None if pd.isna(x) else x).to_dict(orient='records')

    matches_data = safe_to_dict(matches_df)
    teams_data = safe_to_dict(teams_df)
    players_data = safe_to_dict(players_df)
    events_data = safe_to_dict(events_df)

    return matches_data, teams_data, players_data, events_data