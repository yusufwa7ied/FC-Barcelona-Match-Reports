import streamlit as st
import pandas as pd
from data_loader import load_data_from_mongo
from visualizations import plot_pass_network, create_shotmap, create_match_stats_graph_dynamic, create_momentum_graph
from utilities import load_and_resize_logo
from datetime import datetime
import matplotlib.pyplot as plt
import os
from pymongo import MongoClient




st.set_page_config(page_title="FC Barcelona Dashboard", layout="wide")# Custom CSS for centering and controlling the width
st.markdown(
    """
    <style>
    /* Set a maximum width for the main container */
    .appview-container .block-container {
        max-width: 1600px;  /* Adjust as needed for "zoom out" effect */
        margin: 0 auto;  /* Center the container */
        padding: 1rem;  /* Add some padding for aesthetics */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize MongoDB connection
@st.cache_resource
def init_connection():
    MONGO_URI = f"mongodb+srv://{os.getenv('DB_USERNAME', st.secrets['DB_USERNAME'])}:" \
                f"{os.getenv('DB_PASSWORD', st.secrets['DB_PASSWORD'])}@" \
                f"{os.getenv('DB_CLUSTER', st.secrets['DB_CLUSTER'])}.mongodb.net/" \
                f"{os.getenv('DB_NAME', st.secrets['DB_NAME'])}?retryWrites=true&w=majority"
    return MongoClient(MONGO_URI)

client = init_connection()

@st.cache_data
def load_data():
    # Call the function from data_loader to fetch data from MongoDB
    matches_df, teams_df, players_df, events_df = load_data_from_mongo()
    return matches_df, teams_df, players_df, events_df

# Load data (this will now use caching to avoid repeated MongoDB calls)
matches_df, teams_df, players_df, events_df = load_data()

# Create an 'opponent' column to display only the opposing team name in the dropdown
matches_df['opponent'] = matches_df.apply(
    lambda row: row['away_team_name'] if row['home_team_name'] == "Barcelona" else row['home_team_name'], axis=1
)

# Display dropdown for match selection using the opponent name
match_options = matches_df['opponent'].tolist()
selected_opponent = st.sidebar.selectbox("Select Match", match_options)
# Filter the selected match based on the opponent
match_data = matches_df[matches_df['opponent'] == selected_opponent].iloc[0]
match_id = match_data['_id']
home_team_id = match_data['home_team_id']
away_team_id = match_data['away_team_id']

# Generate pass network and momentum plots
home_team_pass_network = plot_pass_network(events_df, match_id, home_team_id, players_df)
away_team_pass_network = plot_pass_network(events_df, match_id, away_team_id, players_df)
match_stats_fig = create_match_stats_graph_dynamic(matches_df, match_id)
momentum_graph = create_momentum_graph(events_df, match_id, home_team_id, away_team_id, interval=3)





# Title
st.markdown("<h1 style='text-align: center; color: white;'>FC Barcelona Match Report</h1>", unsafe_allow_html=True)

# Format date to show only the date part (without time)
match_date = datetime.strptime(str(match_data['date']).split()[0], "%Y-%m-%d").strftime("%d-%m-%Y")

# Row 1: Display match information in the first row
col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    home_logo = load_and_resize_logo(match_data['home_team_name'])
    st.markdown(
        f"""
        <div style='text-align: center; height: 200px; display: flex; flex-direction: column; justify-content: center; align-items: center;'>
            <img src='data:image/png;base64,{home_logo}' width='120' style='object-fit: contain; margin-bottom: 10px;' />
            <h2 style='color: white; margin: 0 0 10px 0; font-size: 28px; font-weight: bold;'></h2>
        </div>
        """, 
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div style='text-align: center;'>
            <h3 style='color: white; font-size: 38px; font-weight: bold;'>{match_date}</h3>
            <h1 style='font-size: 40px; font-weight: bold;'>
                <span style='color: white ;'>{match_data['home_score_fulltime']}</span>
                <span style='color: white;'> - </span>
                <span style='color:white;'>{match_data['away_score_fulltime']}</span>
            </h1>
        </div>
        """, 
        unsafe_allow_html=True
    )

with col3:
    away_logo = load_and_resize_logo(match_data['away_team_name'])
    st.markdown(
        f"""
        <div style='text-align: center; height: 200px; display: flex; flex-direction: column; justify-content: center; align-items: center;'>
            <img src='data:image/png;base64,{away_logo}' width='120' style='object-fit: contain; margin-bottom: 10px;' />
            <h2 style='color: white; margin: 0 0 0px 0; font-size: 28px; font-weight: bold;'></h2>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)  # Adjust the height as needed

# Row 2: Pass Networks and Match Statistics
col4, col5, col6 = st.columns([1, 1, 1])

with col4:
    st.markdown(
        f"<div style='display: flex; flex-direction: column; align-items: center;'>"
        f"<h3 style='text-align: center; color: white; margin-bottom: 0;'>{match_data['home_team_name']} Pass Network</h3>"
        f"</div>",
        unsafe_allow_html=True
    )
    st.pyplot(home_team_pass_network, use_container_width=True)  # Ensures full width in the container

with col5:
    st.markdown(
        "<div class='boxed-section' style='display: flex; flex-direction: column; align-items: center;'>"
        "<h3 style='text-align: center; color: white;'>Match Statistics</h3>"
        "</div>",
        unsafe_allow_html=True
    )
    st.pyplot(match_stats_fig)

with col6:
    st.markdown(
        f"<div style='display: flex; flex-direction: column; align-items: center;'>"
        f"<h3 style='text-align: center; color: white; margin-bottom: 0;'>{match_data['away_team_name']} Pass Network</h3>"
        f"</div>",
        unsafe_allow_html=True
    )
    st.pyplot(away_team_pass_network, use_container_width=True)  # Ensures full width in the container

st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)  # Adjust the height as needed

# Row 3: Shot Maps and xG Flow Chart
col7, col8, col9 = st.columns([1, 1, 1])

with col7:
    st.markdown('<div class="boxed-section">', unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; color: white;'>{match_data['home_team_name']} Shot Map</h3>", unsafe_allow_html=True)
    fig, ax = plt.subplots(figsize=(6, 4))
    home_team_shot_map = create_shotmap(events_df, match_id, home_team_id, ax)
    st.pyplot(home_team_shot_map)
    st.markdown('</div>', unsafe_allow_html=True)

with col8:
    st.markdown('<div class="boxed-section">', unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: white;'>Momentum (Passes in Final Third)</h3>", unsafe_allow_html=True)
    st.pyplot(momentum_graph, use_container_width=True) 
    st.markdown('</div>', unsafe_allow_html=True)

with col9:
    st.markdown('<div class="boxed-section">', unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; color: white;'>{match_data['away_team_name']} Shot Map</h3>", unsafe_allow_html=True)
    fig, ax = plt.subplots(figsize=(6, 4))
    away_team_shot_map = create_shotmap(events_df, match_id, away_team_id, ax)
    st.pyplot(away_team_shot_map)
    st.markdown('</div>', unsafe_allow_html=True)