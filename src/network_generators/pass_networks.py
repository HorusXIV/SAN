"""
Pass Network Generator
Generates pass networks for individual competitions with optimized processing.
"""

from pathlib import Path
from tqdm.auto import tqdm
import pandas as pd
import numpy as np
import networkx as nx
from networkx.algorithms import community
from typing import Optional
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

from src.common import (
    load_json_fixed,
    extract_positions_vectorized,
    extract_start_positions_vectorized,
    find_receivers_kdtree
)
from src.config import (
    DATA_DIR,
    EVENTS_DIR,
    PASS_NETWORKS_DIR,
    PLAYERS_FILE,
    TEAMS_FILE,
    PASS_EVENT_ID,
    ACCURATE_TAG_ID,
    DISTANCE_THRESHOLD,
    TIME_THRESHOLD,
    MAX_WORKERS
)


def check_accurate_vectorized(tags_series):
    """Vectorized accuracy check."""
    def has_accurate_tag(tags):
        if not isinstance(tags, list):
            return False
        return any(tag.get('id') == ACCURATE_TAG_ID for tag in tags)
    
    return pd.Series([has_accurate_tag(tags) for tags in tags_series.values], 
                     index=tags_series.index)


def create_pass_network_optimized(events, df_players, df_teams, competition_name):
    """Optimized pass network creation with vectorized operations."""
    df_events = pd.DataFrame(events)
    df_passes = df_events[df_events['eventId'] == PASS_EVENT_ID].copy()
    
    if len(df_passes) == 0:
        return None
    
    df_passes['accurate'] = check_accurate_vectorized(df_passes['tags'])
    
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
    
    df_passes_network = df_passes_accurate.dropna(subset=['receiver_id'])
    
    if len(df_passes_network) == 0:
        return None
    
    pass_connections = df_passes_network.groupby(['passer_id', 'receiver_id']).agg({
        'accurate': 'mean',
        'pass_distance': 'mean',
        'pass_angle': 'mean'
    }).reset_index()
    pass_connections['pass_count'] = df_passes_network.groupby(['passer_id', 'receiver_id']).size().values
    pass_connections.rename(columns={
        'accurate': 'accuracy',
        'pass_distance': 'avg_pass_distance',
        'pass_angle': 'avg_pass_angle'
    }, inplace=True)
    
    players_involved = set(pass_connections['passer_id']).union(set(pass_connections['receiver_id']))
    players_involved = {pid for pid in players_involved if pid > 0}
    
    players_involved_df = pd.DataFrame(list(players_involved), columns=['player_id'])
    
    player_team_map = df_events.groupby('playerId')['teamId'].agg(
        lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    ).to_dict()
    
    players_involved_df['event_team_id'] = players_involved_df['player_id'].map(player_team_map)
    
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
    
    missing_mask = player_nodes['player_name'].isna()
    if missing_mask.any():
        player_nodes.loc[missing_mask, 'player_name'] = \
            'Unknown_Player_' + player_nodes.loc[missing_mask, 'player_id'].astype(str)
    
    player_nodes['passport_area'] = player_nodes['passport_area'].apply(
        lambda d: d.get('name') if isinstance(d, dict) else d
    )
    player_nodes['position_role'] = player_nodes['position_role'].apply(
        lambda d: d.get('name') if isinstance(d, dict) else d
    )
    
    player_nodes.fillna({
        'weight_kg': 0, 'height_cm': 0, 'birth_date': '',
        'passport_area': 'Unknown', 'position_role': 'Unknown',
        'preferred_foot': 'Unknown', 'current_team_name': 'Unknown',
        'national_team_id': 0, 'currentTeamId': 0
    }, inplace=True)
    
    for col in ['weight_kg', 'height_cm', 'national_team_id', 'currentTeamId']:
        if col in player_nodes.columns:
            player_nodes[col] = pd.to_numeric(player_nodes[col], errors='coerce').fillna(0).astype(int)
    
    player_nodes.set_index('player_id', inplace=True)
    player_nodes.drop(columns=['wyId', 'event_team_id'], errors='ignore', inplace=True)
    
    G = nx.DiGraph()
    
    node_attrs = {int(pid): row.to_dict() for pid, row in player_nodes.iterrows()}
    for pid, attrs in node_attrs.items():
        attrs['label'] = attrs.get('player_name', str(pid))
    G.add_nodes_from(node_attrs.items())
    
    valid_connections = pass_connections[
        (pass_connections['passer_id'] > 0) & 
        (pass_connections['receiver_id'] > 0)
    ]
    
    edges = [
        (int(row['passer_id']), int(row['receiver_id']), {
            'pass_count': int(row['pass_count']),
            'accuracy': float(row['accuracy']),
            'avg_pass_distance': float(row['avg_pass_distance']),
            'avg_pass_angle': float(row['avg_pass_angle']),
            'weight': int(row['pass_count'])
        })
        for _, row in valid_connections.iterrows()
        if row['passer_id'] in player_nodes.index and row['receiver_id'] in player_nodes.index
    ]
    G.add_edges_from(edges)
    
    # Add centrality metrics and k-core
    if len(G.nodes()) > 0 and len(G.edges()) > 0:
        # Convert to undirected for centrality and community detection
        G_undirected = G.to_undirected()
        
        # Calculate centrality metrics
        try:
            # Degree centrality
            degree_centrality = nx.degree_centrality(G)
            nx.set_node_attributes(G, degree_centrality, 'degree_centrality')
            
            # Degree (simple count)
            degree = dict(G.degree())
            nx.set_node_attributes(G, degree, 'degree')
            
            # Betweenness centrality (undirected for consistency)
            betweenness = nx.betweenness_centrality(G_undirected, weight='weight')
            nx.set_node_attributes(G, betweenness, 'betweenness_centrality')
            
            # Closeness centrality (undirected)
            if nx.is_connected(G_undirected):
                closeness = nx.closeness_centrality(G_undirected, distance='weight')
            else:
                # For disconnected graphs, use connected components
                closeness = {}
                for component in nx.connected_components(G_undirected):
                    subgraph = G_undirected.subgraph(component)
                    closeness.update(nx.closeness_centrality(subgraph, distance='weight'))
            nx.set_node_attributes(G, closeness, 'closeness_centrality')
            
            # PageRank
            pagerank = nx.pagerank(G, weight='weight')
            nx.set_node_attributes(G, pagerank, 'pagerank')
        except Exception as e:
            print(f"Warning: Centrality calculation failed for {competition_name}: {e}")
        
        # Calculate k-core numbers
        try:
            kcore = nx.core_number(G_undirected)
            nx.set_node_attributes(G, kcore, 'kcore_number')
        except Exception as e:
            print(f"Warning: K-core calculation failed for {competition_name}: {e}")
    
    # Add modularity class attributes using different community detection algorithms
    if len(G.nodes()) > 0 and len(G.edges()) > 0:
        # Use undirected version for community detection
        G_undirected = G.to_undirected()
        
        # 1. Louvain (greedy modularity communities)
        try:
            louvain_communities = community.greedy_modularity_communities(G_undirected, weight='weight')
            louvain_dict = {}
            for idx, comm in enumerate(louvain_communities):
                for node in comm:
                    louvain_dict[node] = idx
            nx.set_node_attributes(G, louvain_dict, 'modularity_class_louvain')
        except Exception as e:
            print(f"Warning: Louvain community detection failed for {competition_name}: {e}")
        
        # 2. Label Propagation
        try:
            label_prop_communities = community.label_propagation_communities(G_undirected)
            label_prop_dict = {}
            for idx, comm in enumerate(label_prop_communities):
                for node in comm:
                    label_prop_dict[node] = idx
            nx.set_node_attributes(G, label_prop_dict, 'modularity_class_label_propagation')
        except Exception as e:
            print(f"Warning: Label propagation failed for {competition_name}: {e}")
        
        # 3. Greedy (same as Louvain, but with different resolution)
        try:
            greedy_communities = community.greedy_modularity_communities(G_undirected, weight='weight', resolution=1.0)
            greedy_dict = {}
            for idx, comm in enumerate(greedy_communities):
                for node in comm:
                    greedy_dict[node] = idx
            nx.set_node_attributes(G, greedy_dict, 'modularity_class_greedy')
        except Exception as e:
            print(f"Warning: Greedy modularity failed for {competition_name}: {e}")
        
        # 4. Girvan-Newman (computationally expensive, limit to smaller graphs)
        if len(G.nodes()) < 500:  # Only run on smaller graphs due to computational complexity
            try:
                girvan_newman_gen = community.girvan_newman(G_undirected)
                # Get the first level of communities (or could iterate for different levels)
                first_level_communities = next(girvan_newman_gen)
                girvan_dict = {}
                for idx, comm in enumerate(first_level_communities):
                    for node in comm:
                        girvan_dict[node] = idx
                nx.set_node_attributes(G, girvan_dict, 'modularity_class_girvan_newman')
            except Exception as e:
                print(f"Warning: Girvan-Newman failed for {competition_name}: {e}")
    
    return G


def process_single_competition(args):
    """Worker function for parallel processing."""
    event_file, players_data, teams_data = args
    competition_name = event_file.stem.replace('events_', '')
    
    try:
        events = load_json_fixed(event_file)
        df_players = pd.DataFrame(players_data)
        df_teams = pd.DataFrame(teams_data)
        
        G = create_pass_network_optimized(events, df_players, df_teams, competition_name)
        
        if G is not None:
            output_file = PASS_NETWORKS_DIR / f"pass_network_{competition_name}.gexf"
            nx.write_gexf(G, output_file)
            return (competition_name, 'success', output_file)
        else:
            return (competition_name, 'no_data', None)
            
    except Exception as e:
        return (competition_name, 'error', str(e))


def main():
    """Main function with parallel processing."""
    start_time = datetime.now()
    print(f"Starting pass network generation (using {MAX_WORKERS} workers)")
    
    PASS_NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Loading reference data...")
    players = load_json_fixed(PLAYERS_FILE)
    teams = load_json_fixed(TEAMS_FILE)
    
    event_files = list(EVENTS_DIR.glob("events_*.json"))
    print(f"Processing {len(event_files)} competitions")
    
    args_list = [(ef, players, teams) for ef in event_files]
    
    results = []
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_competition, args): args[0] 
                   for args in args_list}
        
        for future in tqdm(as_completed(futures), total=len(futures), 
                          desc="Processing", unit="file"):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error: Future failed: {e}")
    
    success_count = sum(1 for r in results if r[1] == 'success')
    fail_count = len(results) - success_count
    
    duration = datetime.now() - start_time
    print(f"\nComplete: {success_count} successful, {fail_count} failed in {duration}")


if __name__ == "__main__":
    main()
