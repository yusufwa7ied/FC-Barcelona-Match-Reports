# data_loader.py
from pymongo import MongoClient
import pandas as pd
from dotenv import load_dotenv
import os
import streamlit as st


# Load environment variables from .env file
load_dotenv()
def load_data_from_mongo():
    MONGO_URI = f"mongodb+srv://{os.getenv('DB_USERNAME', st.secrets['mongo']['DB_USERNAME'])}:" \
                f"{os.getenv('DB_PASSWORD', st.secrets['mongo']['DB_PASSWORD'])}@" \
                f"{os.getenv('DB_CLUSTER', st.secrets['mongo']['DB_CLUSTER'])}.mongodb.net/" \
                f"{os.getenv('DB_NAME', st.secrets['mongo']['DB_NAME'])}?retryWrites=true&w=majority"
    client = MongoClient(MONGO_URI)
    db = client['fcb2425']
    matches_data = list(db.matches.find())
    teams_data = list(db.teams.find())
    players_data = list(db.players.find())
    events_data = list(db.events.find())
    client.close()
    
    matches_df = pd.DataFrame(matches_data)
    teams_df = pd.DataFrame(teams_data)
    players_df = pd.DataFrame(players_data)
    events_df = pd.DataFrame(events_data)
    
    
    return matches_df, teams_df, players_df, events_df