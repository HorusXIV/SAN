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
from networkx.algorithms import community

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
    UNSUCCESSFUL_TAG_ID,
    INTERCEPTION_TAG_ID,
    DISTANCE_THRESHOLD,
    TIME_THRESHOLD
)


def process_competition_events(events: List[dict], competition_name: str) -> Tuple[pd.DataFrame, Dict]:
    """Process events from a single competition.
    
    Extracts pass events, classifies pass types, identifies receivers,
    and returns network-ready data.
    
    Args:
        events: List of event dictionaries
        competition_name: Name of the competition
        
    Returns:
        Tuple of (passes_dataframe, statistics_dict)
            passes_dataframe: Cleaned passes with receiver information
            statistics_dict: Pass counts by type
    """
    df_events = pd.DataFrame(events)
    df_passes = df_events[df_events['eventId'] == PASS_EVENT_ID].copy()
    
    if len(df_passes) == 0:
        return pd.DataFrame(), {}
    
    def classify_pass(tags):
        if not isinstance(tags, list):
            return 'unsuccessful'
        
        if any(tag.get('id') == INTERCEPTION_TAG_ID for tag in tags):
            return 'intercepted'
        elif any(tag.get('id') == ACCURATE_TAG_ID for tag in tags):
            return 'successful'
        elif any(tag.get('id') == UNSUCCESSFUL_TAG_ID for tag in tags):
            return 'unsuccessful'
        else:
            return 'unsuccessful'
    
    df_passes['pass_type'] = df_passes['tags'].apply(classify_pass)
    
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
    
    df_passes_all = df_passes_clean.copy()
    
    df_events['eventSec'] = pd.to_numeric(df_events['eventSec'], errors='coerce')
    df_passes_all['eventSec'] = pd.to_numeric(df_passes_all['eventSec'], errors='coerce')
    
    df_passes_all['passer_id'] = df_passes_all['playerId']
    df_passes_all['receiver_id'] = find_receivers_kdtree(
        df_passes_all, df_events, DISTANCE_THRESHOLD, TIME_THRESHOLD
    )
    
    df_passes_network = df_passes_all.dropna(subset=['receiver_id']).copy()
    df_passes_network['competition'] = competition_name
    
    stats = {
        'total_passes': len(df_passes),
        'successful_passes': len(df_passes_all[df_passes_all['pass_type'] == 'successful']),
        'unsuccessful_passes': len(df_passes_all[df_passes_all['pass_type'] == 'unsuccessful']),
        'intercepted_passes': len(df_passes_all[df_passes_all['pass_type'] == 'intercepted']),
        'passes_with_receiver': len(df_passes_network),
    }
    
    return df_passes_network, stats


def aggregate_pass_connections(all_passes: pd.DataFrame) -> pd.DataFrame:
    """Aggregate pass connections across all competitions.
    
    Groups passes by passer, receiver, and pass_type, calculating
    statistics for each unique connection.
    
    Args:
        all_passes: DataFrame with passes from all competitions
        
    Returns:
        DataFrame with aggregated pass connections and statistics
    """
    pass_connections = all_passes.groupby(['passer_id', 'receiver_id', 'pass_type']).agg({
        'pass_distance': 'mean',
        'pass_angle': 'mean',
        'competition': lambda x: list(x.unique())
    }).reset_index()
    
    pass_connections['pass_count'] = all_passes.groupby(['passer_id', 'receiver_id', 'pass_type']).size().values
    pass_connections['num_competitions'] = pass_connections['competition'].apply(len)
    
    pass_connections = pass_connections.rename(columns={
        'pass_distance': 'avg_pass_distance',
        'pass_angle': 'avg_pass_angle',
        'competition': 'competitions_list'
    })
    
    return pass_connections


def create_player_nodes(pass_connections: pd.DataFrame, df_players: pd.DataFrame, 
                        df_teams: pd.DataFrame, all_passes: pd.DataFrame) -> pd.DataFrame:
    """Create player nodes with enriched attributes.
    
    Merges player information with pass statistics to create comprehensive
    node attributes for the network.
    
    Args:
        pass_connections: DataFrame with aggregated pass connections
        df_players: DataFrame with player information
        df_teams: DataFrame with team information
        all_passes: DataFrame with all passes for statistics
        
    Returns:
        DataFrame with player nodes and attributes (indexed by player_id)
    """
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
        'competition': lambda x: list(x.unique())
    })
    player_stats.columns = ['avg_pass_distance', 'std_pass_distance', 'competitions_played']
    player_stats['num_competitions'] = player_stats['competitions_played'].apply(len)
    player_stats['total_passes_made'] = all_passes.groupby('passer_id').size()
    
    # Calculate pass accuracy per player
    pass_type_stats = all_passes.groupby(['passer_id', 'pass_type']).size().unstack(fill_value=0)
    if 'successful' in pass_type_stats.columns:
        total_passes = pass_type_stats.sum(axis=1)
        pass_type_stats['pass_accuracy'] = pass_type_stats['successful'] / total_passes
    else:
        pass_type_stats['pass_accuracy'] = 0.0
    
    receiver_stats = all_passes.groupby('receiver_id').agg({
        'pass_distance': 'mean'
    })
    receiver_stats.columns = ['avg_pass_distance_received']
    receiver_stats['total_passes_received'] = all_passes.groupby('receiver_id').size()
    
    player_nodes = player_nodes.merge(
        player_stats, left_on='player_id', right_index=True, how='left'
    ).merge(
        pass_type_stats[['pass_accuracy']], left_on='player_id', right_index=True, how='left', suffixes=('', '_passtype')
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
    """Build unified directed network graph from pass connections.
    
    Creates a NetworkX DiGraph with players as nodes and pass connections
    as edges. Includes centrality metrics and community detection.
    
    Args:
        pass_connections: DataFrame with aggregated pass connections
        player_nodes: DataFrame with player node attributes
        
    Returns:
        NetworkX DiGraph with players and pass connections
    """
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
                'pass_type': str(row['pass_type']),
                'avg_pass_distance': float(row['avg_pass_distance']),
                'avg_pass_angle': float(row['avg_pass_angle']),
                'num_competitions': int(row['num_competitions']),
                'weight': int(row['pass_count'])
            }
            
            if 'competitions_list' in row:
                edge_attrs['competitions'] = ', '.join(row['competitions_list'])
            
            G.add_edge(s, t, **edge_attrs)
            edges_added += 1
    
    # Add centrality metrics and k-core
    if G.number_of_nodes() > 0 and G.number_of_edges() > 0:
        print("Calculating centrality metrics...")
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
            print("  Calculating betweenness centrality (this may take a while)...")
            betweenness = nx.betweenness_centrality(G_undirected, weight='weight')
            nx.set_node_attributes(G, betweenness, 'betweenness_centrality')
            
            # Closeness centrality (undirected)
            print("  Calculating closeness centrality...")
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
            print("  Calculating PageRank...")
            pagerank = nx.pagerank(G, weight='weight')
            nx.set_node_attributes(G, pagerank, 'pagerank')
            
            print("  Centrality metrics calculated")
        except Exception as e:
            print(f"Warning: Centrality calculation failed: {e}")
        
        # Calculate k-core numbers
        try:
            print("Calculating k-core numbers...")
            kcore = nx.core_number(G_undirected)
            nx.set_node_attributes(G, kcore, 'kcore_number')
            print("  K-core numbers calculated")
        except Exception as e:
            print(f"Warning: K-core calculation failed: {e}")
        
        # Community detection (on largest connected component for efficiency)
        print("Running community detection...")
        try:
            # Get largest connected component
            largest_cc = max(nx.connected_components(G_undirected), key=len)
            G_cc = G_undirected.subgraph(largest_cc).copy()
            print(f"  Working with largest connected component: {len(largest_cc)} nodes")
            
            # 1. Louvain (greedy modularity communities)
            print("  Louvain method...")
            louvain_communities = community.greedy_modularity_communities(G_cc, weight='weight')
            louvain_dict = {}
            for idx, comm in enumerate(louvain_communities):
                for node in comm:
                    louvain_dict[node] = idx
            nx.set_node_attributes(G, louvain_dict, 'modularity_class_louvain')
            
            # 2. Label Propagation
            print("  Label propagation...")
            label_prop_communities = community.label_propagation_communities(G_cc)
            label_prop_dict = {}
            for idx, comm in enumerate(label_prop_communities):
                for node in comm:
                    label_prop_dict[node] = idx
            nx.set_node_attributes(G, label_prop_dict, 'modularity_class_label_propagation')
            
            # 3. Greedy Modularity
            print("  Greedy modularity...")
            greedy_communities = community.greedy_modularity_communities(G_cc, weight='weight', resolution=1.0)
            greedy_dict = {}
            for idx, comm in enumerate(greedy_communities):
                for node in comm:
                    greedy_dict[node] = idx
            nx.set_node_attributes(G, greedy_dict, 'modularity_class_greedy')
            
            # 4. Girvan-Newman (only for smaller networks)
            if len(G_cc.nodes()) < 1000:
                print("  Girvan-Newman (this may take a while)...")
                girvan_newman_gen = community.girvan_newman(G_cc)
                first_level_communities = next(girvan_newman_gen)
                girvan_dict = {}
                for idx, comm in enumerate(first_level_communities):
                    for node in comm:
                        girvan_dict[node] = idx
                nx.set_node_attributes(G, girvan_dict, 'modularity_class_girvan_newman')
            else:
                print(f"  Skipping Girvan-Newman (graph too large: {len(G_cc.nodes())} nodes)")
            
            print("  Community detection completed")
        except Exception as e:
            print(f"Warning: Community detection failed: {e}")
    
    return G


def main():
    """Main execution function for unified pass network generation.
    
    Processes all competitions, aggregates pass data, and creates a
    comprehensive network combining all competitions.
    """
    start_time = datetime.now()
    print("Starting unified pass network generation")
    
    PASS_NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Loading reference data...")
    players = load_json_fixed(PLAYERS_FILE)
    teams = load_json_fixed(TEAMS_FILE)
    
    df_players = pd.DataFrame(players)
    df_teams = pd.DataFrame(teams)
    
    event_files = sorted(list(EVENTS_DIR.glob("events_*.json")))
    print(f"Processing {len(event_files)} competitions")
    
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
            print(f"Error processing {competition_name}: {e}")
    
    if not all_passes_list:
        print("Error: No valid pass data found")
        return
    
    all_passes = pd.concat(all_passes_list, ignore_index=True)
    print(f"\nCombined {len(all_passes):,} passes from {len(competition_stats)} competitions")
    
    print("Aggregating pass connections...")
    pass_connections = aggregate_pass_connections(all_passes)
    print("Creating player nodes...")
    player_nodes = create_player_nodes(pass_connections, df_players, df_teams, all_passes)
    print("Building network...")
    G = build_unified_network(pass_connections, player_nodes)
    
    print(f"\nNetwork created: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    
    output_path = PASS_NETWORKS_DIR / 'pass_network_unified.gexf'
    nx.write_gexf(G, output_path)
    print(f"Network saved to {output_path}")
    
    duration = datetime.now() - start_time
    print(f"\nCompleted in {duration}")


if __name__ == "__main__":
    main()
