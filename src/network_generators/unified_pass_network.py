"""
Unified Pass Network Generator
Generates a comprehensive pass network aggregating data from all competitions.
"""

from pathlib import Path
from tqdm.auto import tqdm
import pandas as pd
import numpy as np
import networkx as nx
from typing import Dict, List, Tuple
from datetime import datetime

from src.common import (
    load_json_fixed,
    extract_positions_vectorized,
    extract_start_positions_vectorized,
    setup_logger,
    find_receivers_kdtree
)
from src.config import (
    DATA_DIR,
    LOG_DIR,
    EVENTS_DIR,
    PASS_NETWORKS_DIR,
    PLAYERS_FILE,
    TEAMS_FILE,
    PASS_EVENT_ID,
    ACCURATE_TAG_ID,
    DISTANCE_THRESHOLD,
    TIME_THRESHOLD
)

logger = setup_logger(__name__, log_dir=LOG_DIR, file_prefix='unified_pass_network')


def process_competition_events(events: List[dict], competition_name: str) -> Tuple[pd.DataFrame, Dict]:
    """Process events from a single competition."""
    logger.debug(f"Processing {competition_name}")
    
    df_events = pd.DataFrame(events)
    df_passes = df_events[df_events['eventId'] == PASS_EVENT_ID].copy()
    
    if len(df_passes) == 0:
        return pd.DataFrame(), {}
    
    df_passes['accurate'] = df_passes['tags'].apply(
        lambda x: any(tag['id'] == ACCURATE_TAG_ID for tag in x) if isinstance(x, list) else False
    )
    
    position_data = extract_positions_vectorized(df_passes)
    df_passes = pd.concat([df_passes, position_data], axis=1)
    df_passes_clean = df_passes.dropna(subset=['start_x', 'start_y', 'end_x', 'end_y']).copy()
    
    df_passes_clean['pass_distance'] = np.sqrt(
        (df_passes_clean['end_x'] - df_passes_clean['start_x'])**2 + 
        (df_passes_clean['end_y'] - df_passes_clean['start_y'])**2
    )
    df_passes_clean['pass_angle'] = np.arctan2(
        df_passes_clean['end_y'] - df_passes_clean['start_y'],
        df_passes_clean['end_x'] - df_passes_clean['start_x']
    ) * 180 / np.pi
    
    start_pos = extract_start_positions_vectorized(df_events)
    df_events[['start_x', 'start_y']] = start_pos
    
    df_passes_accurate = df_passes_clean[df_passes_clean['accurate'] == True].copy()
    
    df_events['eventSec'] = pd.to_numeric(df_events['eventSec'], errors='coerce')
    df_passes_accurate['eventSec'] = pd.to_numeric(df_passes_accurate['eventSec'], errors='coerce')
    
    df_passes_accurate['passer_id'] = df_passes_accurate['playerId']
    df_passes_accurate['receiver_id'] = find_receivers_kdtree(
        df_passes_accurate, df_events, DISTANCE_THRESHOLD, TIME_THRESHOLD
    )
    
    df_passes_network = df_passes_accurate.dropna(subset=['receiver_id']).copy()
    df_passes_network['competition'] = competition_name
    
    stats = {
        'total_passes': len(df_passes),
        'accurate_passes': len(df_passes_accurate),
        'passes_with_receiver': len(df_passes_network),
    }
    
    return df_passes_network, stats


def aggregate_pass_connections(all_passes: pd.DataFrame) -> pd.DataFrame:
    """Aggregate pass connections across all competitions."""
    pass_connections = all_passes.groupby(['passer_id', 'receiver_id']).agg({
        'accurate': 'mean',
        'pass_distance': 'mean',
        'pass_angle': 'mean',
        'competition': lambda x: list(x.unique())
    }).reset_index()
    
    pass_connections['pass_count'] = all_passes.groupby(['passer_id', 'receiver_id']).size().values
    pass_connections['num_competitions'] = pass_connections['competition'].apply(len)
    
    pass_connections = pass_connections.rename(columns={
        'accurate': 'accuracy',
        'pass_distance': 'avg_pass_distance',
        'pass_angle': 'avg_pass_angle',
        'competition': 'competitions_list'
    })
    
    return pass_connections


def create_player_nodes(pass_connections: pd.DataFrame, df_players: pd.DataFrame, 
                        df_teams: pd.DataFrame, all_passes: pd.DataFrame) -> pd.DataFrame:
    """Create player nodes with enriched attributes."""
    players_involved = set(pass_connections['passer_id']).union(set(pass_connections['receiver_id']))
    players_involved = {pid for pid in players_involved if pid > 0}
    
    players_involved_df = pd.DataFrame(list(players_involved), columns=['player_id'])
    
    player_team_map = all_passes.groupby('passer_id')['teamId'].agg(
        lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    ).to_dict()
    
    receiver_team_map = all_passes.groupby('receiver_id')['teamId'].agg(
        lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    ).to_dict()
    
    combined_team_map = {**receiver_team_map, **player_team_map}
    
    players_involved_df['event_team_id'] = players_involved_df['player_id'].map(combined_team_map)
    
    player_nodes = players_involved_df.merge(
        df_players[['passportArea', 'weight', 'birthDate', 'height', 'role', 'wyId', 
                    'foot', 'shortName', 'currentNationalTeamId']], 
        left_on='player_id', right_on='wyId', how='left'
    )
    
    player_nodes = player_nodes.merge(
        df_teams[['wyId', 'name']].rename(columns={'wyId': 'event_team_id', 'name': 'current_team_name'}),
        on='event_team_id', how='left'
    )
    
    player_nodes['currentTeamId'] = player_nodes['event_team_id']
    
    player_nodes.rename(columns={
        'weight': 'weight_kg',
        'birthDate': 'birth_date',
        'passportArea': 'passport_area',
        'height': 'height_cm',
        'role': 'position_role',
        'foot': 'preferred_foot',
        'shortName': 'player_name',
        'currentNationalTeamId': 'national_team_id'
    }, inplace=True)
    
    missing_data_mask = player_nodes['player_name'].isna()
    if missing_data_mask.any():
        player_nodes.loc[missing_data_mask, 'player_name'] = player_nodes.loc[missing_data_mask, 'player_id'].apply(
            lambda x: f"Unknown_Player_{int(x)}"
        )
    
    player_nodes['passport_area'] = player_nodes['passport_area'].apply(
        lambda d: d.get('name') if isinstance(d, dict) else d
    )
    player_nodes['position_role'] = player_nodes['position_role'].apply(
        lambda d: d.get('name') if isinstance(d, dict) else d
    )
    
    player_stats = all_passes.groupby('passer_id').agg({
        'pass_distance': ['mean', 'std'],
        'accurate': 'mean',
        'competition': lambda x: list(x.unique())
    })
    player_stats.columns = ['avg_pass_distance', 'std_pass_distance', 'pass_accuracy', 'competitions_played']
    player_stats['num_competitions'] = player_stats['competitions_played'].apply(len)
    player_stats['total_passes_made'] = all_passes.groupby('passer_id').size()
    
    receiver_stats = all_passes.groupby('receiver_id').agg({
        'pass_distance': 'mean'
    })
    receiver_stats.columns = ['avg_pass_distance_received']
    receiver_stats['total_passes_received'] = all_passes.groupby('receiver_id').size()
    
    player_nodes = player_nodes.merge(
        player_stats, left_on='player_id', right_index=True, how='left'
    ).merge(
        receiver_stats, left_on='player_id', right_index=True, how='left'
    )
    
    player_nodes = player_nodes.fillna({
        'weight_kg': 0, 'height_cm': 0, 'birth_date': '',
        'passport_area': 'Unknown', 'position_role': 'Unknown',
        'preferred_foot': 'Unknown', 'current_team_name': 'Unknown',
        'national_team_id': 0, 'currentTeamId': 0,
        'avg_pass_distance': 0.0, 'std_pass_distance': 0.0,
        'pass_accuracy': 0.0, 'num_competitions': 0,
        'total_passes_made': 0, 'avg_pass_distance_received': 0.0,
        'total_passes_received': 0
    })
    
    player_nodes = player_nodes.drop(columns=['competitions_played'], errors='ignore')
    player_nodes = player_nodes.set_index('player_id')
    player_nodes = player_nodes.drop(columns=['wyId', 'event_team_id'], errors='ignore')
    
    numeric_cols = ['weight_kg', 'height_cm', 'national_team_id', 'currentTeamId', 
                    'num_competitions', 'total_passes_made', 'total_passes_received']
    for col in numeric_cols:
        if col in player_nodes.columns:
            player_nodes[col] = pd.to_numeric(player_nodes[col], errors='coerce').fillna(0).astype(int)
    
    float_cols = ['avg_pass_distance', 'std_pass_distance', 'pass_accuracy', 'avg_pass_distance_received']
    for col in float_cols:
        if col in player_nodes.columns:
            player_nodes[col] = pd.to_numeric(player_nodes[col], errors='coerce').fillna(0.0).astype(float)
    
    return player_nodes


def build_unified_network(pass_connections: pd.DataFrame, player_nodes: pd.DataFrame) -> nx.DiGraph:
    """Build unified directed network graph."""
    G = nx.DiGraph()
    
    for pid, attrs in player_nodes.iterrows():
        node_attrs = attrs.to_dict()
        node_attrs['label'] = node_attrs.get('player_name', str(pid))
        G.add_node(int(pid), **node_attrs)
    
    edges_added = 0
    
    for _, row in pass_connections.iterrows():
        s = int(row['passer_id'])
        t = int(row['receiver_id'])
        
        if s <= 0 or t <= 0:
            continue
        
        if s in player_nodes.index and t in player_nodes.index:
            edge_attrs = {
                'pass_count': int(row['pass_count']),
                'accuracy': float(row['accuracy']),
                'avg_pass_distance': float(row['avg_pass_distance']),
                'avg_pass_angle': float(row['avg_pass_angle']),
                'num_competitions': int(row['num_competitions']),
                'weight': int(row['pass_count'])
            }
            
            if 'competitions_list' in row:
                edge_attrs['competitions'] = ', '.join(row['competitions_list'])
            
            G.add_edge(s, t, **edge_attrs)
            edges_added += 1
    
    return G


def main():
    """Main execution function."""
    start_time = datetime.now()
    logger.info("Starting unified pass network generation")
    
    PASS_NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("Loading reference data")
    players = load_json_fixed(PLAYERS_FILE)
    teams = load_json_fixed(TEAMS_FILE)
    
    df_players = pd.DataFrame(players)
    df_teams = pd.DataFrame(teams)
    
    event_files = sorted(list(EVENTS_DIR.glob("events_*.json")))
    logger.info(f"Processing {len(event_files)} competitions")
    
    all_passes_list = []
    competition_stats = {}
    
    for event_file in tqdm(event_files, desc="Competitions"):
        competition_name = event_file.stem.replace('events_', '')
        
        try:
            events = load_json_fixed(event_file)
            passes_df, stats = process_competition_events(events, competition_name)
            
            if len(passes_df) > 0:
                all_passes_list.append(passes_df)
                competition_stats[competition_name] = stats
                
        except Exception as e:
            logger.error(f"Error processing {competition_name}: {e}")
    
    if not all_passes_list:
        logger.error("No valid pass data found")
        return
    
    all_passes = pd.concat(all_passes_list, ignore_index=True)
    logger.info(f"Combined {len(all_passes):,} passes from {len(competition_stats)} competitions")
    
    pass_connections = aggregate_pass_connections(all_passes)
    player_nodes = create_player_nodes(pass_connections, df_players, df_teams, all_passes)
    G = build_unified_network(pass_connections, player_nodes)
    
    logger.info(f"Network created: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    
    output_path = PASS_NETWORKS_DIR / 'pass_network_unified.gexf'
    nx.write_gexf(G, output_path)
    logger.info(f"Network saved to {output_path}")
    
    duration = datetime.now() - start_time
    logger.info(f"Completed in {duration}")


if __name__ == "__main__":
    main()
