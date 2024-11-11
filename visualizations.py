import pandas as pd
import math
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms

# Filter match events up to the first substitution or halftime
def filter_match_events(events_data, match_id, team_id):
    match_events = events_data[(events_data['match_id'] == match_id) & 
                               (events_data['team_id'] == team_id)]
    
    # Find the time of the first substitution
    sub_df = match_events.loc[(match_events['type'] == "SubstitutionOn")]
    first_sub = sub_df["total_seconds"].min()

    # Cap it at halftime if the first substitution was in the first half
    if first_sub <= (60 * 45):
        first_sub = 60 * 45

    # Filter events to only passes before the first substitution
    match_events = match_events.loc[match_events['total_seconds'] < first_sub]
    match_events = match_events[(match_events['type'] == 'Pass') & 
                            (match_events['type_outcome'] == 'Successful')]
    return match_events

# Calculate average locations and pass counts
def calculate_average_locations_and_pass_counts(match_events, players_data):

    # Calculate average locations and pass counts for each player
    average_locs_and_count = match_events.groupby('passer').agg({'x': 'mean', 'y':['mean','count']})
    average_locs_and_count.columns = ['x', 'y', 'count']

    # Find number of passes between each player-pair path
    passes_between = match_events.groupby(['passer', 'recipient'])['_id'].count().reset_index()
    passes_between.rename({'_id': 'pass_count'}, axis='columns', inplace=True)

    # Merge pass counts with average locations for plotting
    passes_between = passes_between.merge(average_locs_and_count, left_on='passer', right_index=True)
    passes_between = passes_between.merge(average_locs_and_count, left_on='recipient', right_index=True, suffixes=['', '_end'])
    passes_between = passes_between.loc[(passes_between['pass_count'] >= 4)]  # Threshold for pass display

    # Merge in player jersey numbers
    players_data['player_id'] = players_data['_id'].apply(lambda x: int(x.split('_')[0]))
    average_locs_and_count = average_locs_and_count.merge(players_data[['player_id', 'shirt_no']], left_index=True, right_on='player_id')

    return average_locs_and_count, passes_between

def pass_line_template(ax, x, y, end_x, end_y, line_color='#A50044', head_color='#FDCB13'):
    """Draws an arrow between two points with different colors for the line and arrowhead."""
    ax.annotate(
        '',
        xy=(end_y, end_x),         # Arrow endpoint
        xytext=(y, x),             # Arrow startpoint
        zorder=1,
        arrowprops=dict(
            arrowstyle='-|>,head_width=0.4,head_length=0.8',  # Arrowhead style with custom dimensions
            linewidth=3,                                     # Line thickness
            color=line_color,                                # Line color
            alpha=0.85,
            shrinkA=0,                                       # Ensures no gap on start
            shrinkB=0,                                       # Ensures no gap on end
            mutation_scale=8,                               # Scales the arrowhead
            fc=head_color                                    # Fill color for the arrowhead
        )
    )

def pass_line_template_shrink(ax, x, y, end_x, end_y, line_color='#A50044', dist_delta=1.2):
    """Shortens arrow length to stop at the edge of player circles."""
    dist = math.hypot(end_x - x, end_y - y)
    angle = math.atan2(end_y - y, end_x - x)
    upd_x = x + (dist - dist_delta) * math.cos(angle)
    upd_y = y + (dist - dist_delta) * math.sin(angle)
    pass_line_template(ax, x, y, upd_x, upd_y, line_color=line_color)

#plot the pass network
def plot_pass_network(events_data, match_id, team_id, players_data):
    # Filter events before the first substitution
    match_events = filter_match_events(events_data, match_id, team_id)

    # Calculate average locations and pass counts
    average_locs_and_count, passes_between = calculate_average_locations_and_pass_counts(match_events, players_data)

    # Set up the pitch
    pitch = VerticalPitch(pitch_type='custom', pitch_length=100, pitch_width=100, line_color='#FDCB13', pitch_color='#0A0A2A', line_zorder=1)
    fig, ax = pitch.draw(figsize=(8, 4))
    fig.patch.set_facecolor('#0A0A2A')
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_position([0, 0, 1, 1])

    # Plot arrows for passes
    line_width = 1
    for index, row in passes_between.iterrows():
        line_width = row['pass_count'] / 4  # Adjust line width based on pass count
        pass_line_template_shrink(ax, row['x'], row['y'], row['x_end'], row['y_end'], '#A50044')

    # Plot player locations
    pitch.scatter(
        average_locs_and_count['x'], average_locs_and_count['y'], s=500,
        color='#FDCB13', edgecolors="#A50044", linewidth=line_width, alpha=1, ax=ax, zorder=2
    )

    # Annotate jersey numbers
    for index, row in average_locs_and_count.iterrows():
        pitch.annotate(
            str(int(row['shirt_no'])),
            xy=(row.x, row.y),
            c='#0A0A2A',
            va='center',
            ha='center',
            size=10,
            fontweight='bold',
            ax=ax
        )

    return fig

#plot the shot map
def create_shotmap(events_df, match_id, team_id, ax):
    # Set up the pitch with half field view in theme colors
    pitch = VerticalPitch(
        pitch_type='custom', pitch_length=100, pitch_width=100, half=True, 
        line_color='#FDCB13', pitch_color='#0A0A2A', line_zorder=1,linewidth=3
    )
    pitch.draw(ax=ax)
    fig = ax.get_figure()
    fig.patch.set_facecolor('#0A0A2A')
    ax.set_position([0, 0, 1, 1])
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    # Filter shots for the specified match and team
    team_shots = events_df[
        (events_df['match_id'] == match_id) & 
        (events_df['team_id'] == team_id) & 
        (events_df['type'].isin(['Goal', 'SavedShot', 'MissedShots', 'ShotOnPost']))
    ]
    
    # Plot each shot based on its outcome
    for _, shot in team_shots.iterrows():
        line_width = 0.8 
        if shot['type'] == 'Goal':
            marker = 'o'  # Circle for goals
            color = '#00FF00'  # Green for goals
            size = 300  # Larger size for goals
            line_width = 0.8  # Standard line width for circles
        elif shot['type'] == 'SavedShot':
            marker = 's'  # Square for saved shots
            color = '#A50044'  # Custom red for saved shots
            size = 100  # Smaller size for saved shots
            line_width = 0.8  # Standard line width for squares
        elif shot['type'] in ['MissedShots', 'ShotOnPost']:  # Combine missed shots and shots on post
            marker = 'x'  # Cross for missed shots
            color = '#FDCB13'  # Yellow for missed shots
            size = 100  # Smaller size for missed shots
            line_width = 2  # Increase line width for "X" to make it bolder
        
        # Plot the shot
        pitch.scatter(
            shot['x'], shot['y'], ax=ax, s=size, color=color, marker=marker,
            edgecolor='black', linewidth=line_width, alpha=0.8
        )
        
    # Add a legend with theme-consistent colors
    ax.legend(handles=[
        plt.Line2D([0], [0], marker='o', color='#00FF00', label='Goal', markersize=10, markerfacecolor='#00FF00', markeredgecolor='black'),
        plt.Line2D([0], [0], marker='s', color='#A50044', label='Saved Shot', markersize=10, markerfacecolor='#A50044', markeredgecolor='black'),
        plt.Line2D([0], [0], marker='X', color='#FDCB13', label='Missed Shot', markersize=10, markeredgecolor='black')
    ], loc='lower left', frameon=False, labelcolor='white',
              bbox_to_anchor=(0, 0.05) )

    # Remove padding and ensure the pitch takes up the full axis space
    ax.set_position([0, 0, 1, 1])
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)


    return fig

#plot the stats
def create_match_stats_graph_dynamic(matches_df, match_id):
    # Get match-specific data from the dataframe
    match_data = matches_df[matches_df['_id'] == match_id].iloc[0]
    
    # Determine if Barcelona is the home or away team and set colors and positions accordingly
    if match_data['home_team_name'] == "Barcelona":
        barcelona_name, barcelona_color = "Barcelona", "#A50044"  # Red for Barcelona
        opponent_name, opponent_color = match_data['away_team_name'], "#FDCB13"  # Yellow for opponent
        total_possession = match_data['home_possession'] + match_data['away_possession']
        home_possession_exact = match_data['home_possession'] / total_possession * 100
        away_possession_exact = match_data['away_possession'] / total_possession * 100

        # Round the home team's possession and adjust the away team's possession
        home_possession_percentage = round(home_possession_exact)
        away_possession_percentage = 100 - home_possession_percentage
                
        
        
        
        barcelona_stats = {
        "Possession (%)": home_possession_percentage,
        "Total Shots": int(match_data['home_shots_total']),
        "Shots on Target": int(match_data['home_shots_on_target']),
        "Total Passes": int(match_data['home_passes_total']),
        "Pass Completion (%)": int(round((match_data['home_pass_completion'] / match_data['home_passes_total']) * 100)),
        "Corners": int(match_data['home_corners']),
        "Offsides": int(match_data['home_offsides_caught'])
    }

        opponent_stats = {
        "Possession (%)": away_possession_percentage,
        "Total Shots": int(match_data['away_shots_total']),
        "Shots on Target": int(match_data['away_shots_on_target']),
        "Total Passes": int(match_data['away_passes_total']),
        "Pass Completion (%)": int(round((match_data['away_pass_completion'] / match_data['away_passes_total']) * 100)),
        "Corners": int(match_data['away_corners']),
        "Offsides": int(match_data['away_offsides_caught'])
    }
        barcelona_left = False  # Set Barcelona on the left for this case
    else:
        opponent_name, opponent_color = match_data['home_team_name'], "#FDCB13"  # Yellow for opponent
        barcelona_name, barcelona_color = "Barcelona", "#A50044"  # Red for Barcelona
        total_possession = match_data['home_possession'] + match_data['away_possession']
        home_possession_exact = match_data['home_possession'] / total_possession * 100
        away_possession_exact = match_data['away_possession'] / total_possession * 100
        home_possession_percentage = round(home_possession_exact)
        away_possession_percentage = 100 - home_possession_percentage
        opponent_stats = {
            "Possession (%)":  home_possession_percentage,
            "Total Shots": match_data['home_shots_total'],
            "Shots on Target": match_data['home_shots_on_target'],
            "Total Passes": match_data['home_passes_total'],
            "Pass Completion (%)": (match_data['home_pass_completion'] / match_data['home_passes_total']) * 100,
            "Corners": match_data['home_corners'],
            "Offsides": match_data['home_offsides_caught']
        }
        barcelona_stats = {
            "Possession (%)": away_possession_percentage,
            "Total Shots": match_data['away_shots_total'],
            "Shots on Target": match_data['away_shots_on_target'],
            "Total Passes": match_data['away_passes_total'],
            "Pass Completion (%)": (match_data['away_pass_completion'] / match_data['away_passes_total']) * 100,
            "Corners": match_data['away_corners'],
            "Offsides": match_data['away_offsides_caught']
        }
        barcelona_left = True  # Set Barcelona on the right for this case

    # Create figure
    stats = ["Possession (%)", "Total Shots", "Shots on Target", "Total Passes", "Pass Completion (%)", "Corners", "Offsides"]
    fig, axes = plt.subplots(len(stats), 1, figsize=(11, len(stats) * 1.5), facecolor="#0A0A2A")

    line_offset = -0.003
    # Loop through each stat and create a back-to-back horizontal bar chart
    for ax, stat in zip(axes, stats):
        barcelona_stat = barcelona_stats[stat]
        opponent_stat = opponent_stats[stat]
        max_val = max(barcelona_stat, opponent_stat)
        
        ax.set_ylim(-0.15, 0.15)
        

        if barcelona_left:
            # Barcelona stats on the left
            trans = transforms.blended_transform_factory(ax.transData, ax.transData + transforms.ScaledTranslation(0, line_offset, ax.figure.dpi_scale_trans))
            ax.barh(stat, barcelona_stat, color=barcelona_color,height=0.05, align='center')
            ax.barh(stat, -opponent_stat, color=opponent_color,height=0.05, align='center')
            # Labels and colored underlines
            ax.text(max_val * 1.1, stat, f"{int(barcelona_stat)}", va='center', ha='left', color='white', fontsize=22,fontweight='bold')
            ax.text(-max_val * 1.1, stat, f"{int(opponent_stat)}", va='center', ha='right', color='white', fontsize=22,fontweight='bold')
            ax.hlines(y=line_offset, xmin=0, xmax=max_val, color=barcelona_color, linewidth=2.5)
            ax.hlines(y=line_offset, xmin=-max_val, xmax=0, color=opponent_color, linewidth=2.5)
        else:
            # Barcelona stats on the right
            trans = transforms.blended_transform_factory(ax.transData, ax.transData + transforms.ScaledTranslation(0, line_offset, ax.figure.dpi_scale_trans))
            ax.barh(stat, -barcelona_stat, color=barcelona_color, height=0.03, align='edge')
            ax.barh(stat, opponent_stat, color=opponent_color, height=0.03, align='edge')
            # Labels and colored underlines
            ax.text(max_val * 1.1, stat, f"{int(opponent_stat)}", va='center', ha='left', color='white', fontsize=25,fontweight='bold')
            ax.text(-max_val * 1.1, stat, f"{int(barcelona_stat)}", va='center', ha='right', color='white', fontsize=25,fontweight='bold')
            ax.hlines(y=line_offset, xmin=-max_val, xmax=0, color=barcelona_color, linewidth=2.5)
            ax.hlines(y=line_offset, xmin=0, xmax=max_val, color=opponent_color, linewidth=2.5)

        # Set x-axis limits and remove bottom border
        ax.set_xlim(-max_val * 1.2, max_val * 1.2)
        ax.spines['bottom'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Customize appearance
        ax.set_facecolor("#0A0A2A")
        #ax.set_title(stat, color="white", loc="center", fontsize=25, pad=20, fontweight='bold')
        ax.text(0, 0.10, stat, color="white", ha='center', va='bottom', fontsize=23, fontweight='bold')
        ax.tick_params(left=False, bottom=False)
        ax.set_xticks([])
        ax.set_yticklabels([])

    plt.tight_layout(pad=1)
    return fig

#plot the stats
def create_momentum_graph(events_df, match_id, home_team_id, away_team_id, interval=3):
    # Ensure Barcelona is always assigned the red color
    barcelona_color = '#A50044'  # Red for Barcelona
    opponent_color = '#FDCB13'   # Yellow for opponent
    if home_team_id == 65: # Assuming 65 is the team_id for Barcelona
        home_color = barcelona_color
        away_color = opponent_color
    else:
        home_color = opponent_color
        away_color = barcelona_color
    # Filter data for the specified match and only include pass events in the final third
    match_events = events_df[(events_df['match_id'] == match_id) & (events_df['type'] == 'Pass')]
    # Filter for goal events within the specified match
    goal_events = events_df[(events_df['match_id'] == match_id) & (events_df['type'] == 'Goal')]
    # Identify final third for each team
    home_passes_final_third = match_events[(match_events['team_id'] == home_team_id) & (match_events['end_x'] >= 66.7)]
    away_passes_final_third = match_events[(match_events['team_id'] == away_team_id) & (match_events['end_x'] <= 33.3)]

    # Group by time intervals
    home_pass_intervals = home_passes_final_third.groupby((home_passes_final_third['minute'] // interval) * interval).size()
    away_pass_intervals = away_passes_final_third.groupby((away_passes_final_third['minute'] // interval) * interval).size()

    # Create a DataFrame for plotting
    momentum_df = pd.DataFrame({'Home Passes in Final Third': home_pass_intervals, 'Away Passes in Final Third': away_pass_intervals}).fillna(0)

    # Plot
    # Adjusted Plotting Section
    fig, ax = plt.subplots(figsize=(24, 14), dpi=150, facecolor="#0A0A2A")

    # Plot Barcelona's passes above 50 and the opponent's below 50
    ax.plot(momentum_df.index, 50 + momentum_df['Home Passes in Final Third'], color=home_color, label='Barcelona Passes in Final Third')
    ax.plot(momentum_df.index, 50 - momentum_df['Away Passes in Final Third'], color=away_color, label='Opponent Passes in Final Third')

    # Fill area between the lines and 50 for a clearer visual separation
    ax.fill_between(momentum_df.index, 50, 50 + momentum_df['Home Passes in Final Third'], color=home_color, alpha=0.4)
    ax.fill_between(momentum_df.index, 50, 50 - momentum_df['Away Passes in Final Third'], color=away_color, alpha=0.4)
    # Add goal markers
    # Add goal markers
    for _, goal in goal_events.iterrows():
        goal_minute = goal['minute']
        goal_team = goal['team_id']

        if goal_team == home_team_id:
            # Plot goal for home team directly on the peak of that interval
            y_position = 50 + momentum_df['Home Passes in Final Third'].get(goal_minute // interval * interval, 0)
            ax.scatter(goal_minute, y_position, color=home_color, edgecolor="white", s=900, zorder=3, marker='o', label='Goal' if 'Goal' not in ax.get_legend_handles_labels()[1] else "")
        else:
            # Plot goal for away team directly on the peak of that interval
            y_position = 50 - momentum_df['Away Passes in Final Third'].get(goal_minute // interval * interval, 0)
            ax.scatter(goal_minute, y_position, color=away_color, edgecolor="white", s=900, zorder=3, marker='o', label='Goal' if 'Goal' not in ax.get_legend_handles_labels()[1] else "")

    
    # Customize appearance
    ax.spines['bottom'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_facecolor("#0A0A2A")
    ax.axhline(y=50, color="white", linestyle='--', linewidth=0.5)
    ax.tick_params(colors="white")

    plt.xticks(momentum_df.index)
    ax.set_yticks([])
    plt.grid(False)
    # Set x-ticks to every 10 minutes
    ax.set_xticks(range(0, int(momentum_df.index.max()) + interval, 10))
    #ax.tick_params(axis='x', labelsize=30, colors='white', labelweight='bold')  # Adjust labelsize as needed
    for label in ax.get_xticklabels():
        label.set_fontsize(33)  # Set label size
        label.set_color('white')  # Set label color
        label.set_fontweight('bold')  # Set label weight to bold

    # Ensure x-axis starts at 0 without shifting
    ax.set_xlim(left=-1, right=momentum_df.index[-1])

    return fig

