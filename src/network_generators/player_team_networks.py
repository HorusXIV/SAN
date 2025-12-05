"""
Player-Team Network Generator
Creates bipartite networks connecting players to teams they've played for or against.
"""

import networkx as nx
import pandas as pd
from pathlib import Path
from collections import defaultdict
from tqdm.auto import tqdm

from src.common import load_json_fixed, setup_logger
from src.config import (
    DATA_DIR,
    LOG_DIR,
    EVENTS_DIR,
    PLAYER_TEAM_NETWORKS_DIR,
    PLAYERS_FILE,
    TEAMS_FILE
)

logger = setup_logger(__name__, log_dir=LOG_DIR, file_prefix='player_team_network')


def extract_player_team_interactions(events, competition_name):
    """Extract player-team interactions from events."""
    df_events = pd.DataFrame(events)
    
    if 'playerId' not in df_events.columns or 'teamId' not in df_events.columns:
        return pd.DataFrame()
    
    df_clean = df_events[['playerId', 'teamId', 'matchId']].dropna()
    
    interactions = df_clean.groupby(['playerId', 'teamId']).agg({
        'matchId': lambda x: len(x.unique())
    }).reset_index()
    interactions.columns = ['player_id', 'team_id', 'matches_together']
    interactions['competition'] = competition_name
    
    return interactions


def create_player_team_network(interactions_df, players_data, teams_data, competition_name):
    """Create bipartite network of players and teams."""
    G = nx.Graph()
    G.graph['competition'] = competition_name
    G.graph['graph_type'] = 'bipartite'
    
    player_stats = defaultdict(lambda: {
        'teams_played_for': set(),
        'total_matches': 0,
        'total_interactions': 0
    })
    
    team_stats = defaultdict(lambda: {
        'players': set(),
        'total_matches': 0,
        'total_interactions': 0
    })
    
    for _, row in interactions_df.iterrows():
        player_id = int(row['player_id'])
        team_id = int(row['team_id'])
        matches = int(row['matches_together'])
        
        player_stats[player_id]['teams_played_for'].add(team_id)
        player_stats[player_id]['total_matches'] += matches
        player_stats[player_id]['total_interactions'] += 1
        
        team_stats[team_id]['players'].add(player_id)
        team_stats[team_id]['total_matches'] += matches
        team_stats[team_id]['total_interactions'] += 1
        
        if not G.has_edge(player_id, team_id):
            G.add_edge(player_id, team_id, 
                      matches_together=matches,
                      weight=matches)
        else:
            G[player_id][team_id]['matches_together'] += matches
            G[player_id][team_id]['weight'] += matches
    
    player_lookup = {p['wyId']: p for p in players_data}
    team_lookup = {t['wyId']: t for t in teams_data}
    
    for node in G.nodes():
        if node in player_lookup:
            player = player_lookup[node]
            G.nodes[node].update({
                'type': 'player',
                'label': player.get('shortName', f'Player_{node}'),
                'name': player.get('shortName', 'Unknown'),
                'role': player.get('role', {}).get('name', 'Unknown') if isinstance(player.get('role'), dict) else 'Unknown',
                'area': player.get('passportArea', {}).get('name', 'Unknown') if isinstance(player.get('passportArea'), dict) else 'Unknown',
                'teams_count': len(player_stats[node]['teams_played_for']),
                'total_matches': player_stats[node]['total_matches'],
                'bipartite': 0
            })
        elif node in team_lookup:
            team = team_lookup[node]
            G.nodes[node].update({
                'type': 'team',
                'label': team.get('name', f'Team_{node}'),
                'name': team.get('name', 'Unknown'),
                'area': team.get('area', {}).get('name', 'Unknown') if isinstance(team.get('area'), dict) else 'Unknown',
                'players_count': len(team_stats[node]['players']),
                'total_matches': team_stats[node]['total_matches'],
                'bipartite': 1
            })
        else:
            G.nodes[node]['label'] = f'Unknown_{node}'
            G.nodes[node]['type'] = 'unknown'
    
    return G


def process_competition(event_file, players_data, teams_data):
    """Process a single competition's events."""
    competition_name = event_file.stem.replace('events_', '')
    
    events = load_json_fixed(event_file)
    
    interactions = extract_player_team_interactions(events, competition_name)
    
    if len(interactions) == 0:
        logger.warning(f"No interactions found for {competition_name}")
        return None
    
    G = create_player_team_network(interactions, players_data, teams_data, competition_name)
    
    return competition_name, G


def main():
    """Main execution function."""
    logger.info("Starting Player-Team Network Generation")
    
    PLAYER_TEAM_NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    
    players = load_json_fixed(PLAYERS_FILE)
    teams = load_json_fixed(TEAMS_FILE)
    logger.info(f"Loaded {len(players)} players, {len(teams)} teams")
    
    event_files = sorted(list(EVENTS_DIR.glob("events_*.json")))
    logger.info(f"Processing {len(event_files)} competitions")
    
    results = []
    for event_file in tqdm(event_files, desc="Generating networks"):
        result = process_competition(event_file, players, teams)
        if result:
            results.append(result)
    
    for competition_name, G in results:
        output_file = PLAYER_TEAM_NETWORKS_DIR / f'player_team_network_{competition_name}.gexf'
        nx.write_gexf(G, output_file)
        logger.info(f"{competition_name}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    logger.info(f"Generated {len(results)} player-team networks")


if __name__ == "__main__":
    main()
