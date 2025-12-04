"""
Unified Pass Network Generator
==============================
Generates a comprehensive pass network aggregating data from all competitions.

Features:
- Aggregates pass data from multiple competitions
- Normalizes player interactions across different contexts
- Optimized for large-scale data processing
- Provides detailed statistics and validation
- Exports unified network in multiple formats
- Modular design for easy maintenance

Author: Generated for FHNW Semester 3 SAN
Date: 2025-12-04
"""

import json
from pathlib import Path
from tqdm.auto import tqdm
import pandas as pd
import numpy as np
import networkx as nx
from typing import Dict, Set, List, Tuple, Optional
import logging
from datetime import datetime
from collections import defaultdict


# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path('data')
EVENTS_DIR = DATA_DIR / 'events'
NETWORKS_DIR = DATA_DIR / 'Networks'
PASS_EVENT_ID = 8
ACCURATE_TAG_ID = 1801

# Network generation parameters
DISTANCE_THRESHOLD = 5.0  # Maximum distance to identify receiver (units)
TIME_THRESHOLD = 5.0      # Maximum time window to identify receiver (seconds)

# Setup logging
log_file = DATA_DIR / f'unified_network_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def fix_unicode_escapes(obj):
    """Recursively decode \\uXXXX sequences in all strings."""
    if isinstance(obj, str):
        if r"\u" in obj:
            try:
                return obj.encode("utf-8").decode("unicode_escape")
            except UnicodeDecodeError:
                return obj
        return obj
    elif isinstance(obj, list):
        return [fix_unicode_escapes(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: fix_unicode_escapes(v) for k, v in obj.items()}
    else:
        return obj


def load_json_fixed(path: Path) -> any:
    """Load JSON file with unicode escape fix."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return fix_unicode_escapes(data)


def extract_positions(row) -> pd.Series:
    """Extract start and end positions from event data."""
    positions = row.get('positions', [])
    if len(positions) >= 2:
        start = positions[0]
        end = positions[1]
        return pd.Series({
            'start_x': start['x'],
            'start_y': start['y'],
            'end_x': end['x'],
            'end_y': end['y']
        })
    return pd.Series({'start_x': None, 'start_y': None, 'end_x': None, 'end_y': None})


def extract_start_position(positions) -> Tuple[Optional[float], Optional[float]]:
    """Extract start x,y from positions array."""
    if positions and len(positions) > 0:
        return positions[0].get('x'), positions[0].get('y')
    return None, None


# ============================================================================
# DATA PROCESSING FUNCTIONS
# ============================================================================

def find_receivers_vectorized(
    passes_df: pd.DataFrame, 
    events_df: pd.DataFrame, 
    distance_threshold: float = DISTANCE_THRESHOLD, 
    time_threshold: float = TIME_THRESHOLD
) -> pd.Series:
    """
    Find pass receivers using optimized vectorized approach.
    
    Args:
        passes_df: DataFrame of pass events
        events_df: DataFrame of all events
        distance_threshold: Maximum distance to identify receiver
        time_threshold: Maximum time window to identify receiver
        
    Returns:
        Series of receiver IDs indexed by pass DataFrame index
    """
    # Prepare events: filter and sort
    events_sorted = events_df[['matchId', 'eventSec', 'playerId', 'teamId', 'start_x', 'start_y']].copy()
    events_sorted = events_sorted.dropna(subset=['start_x', 'start_y'])
    events_sorted = events_sorted.sort_values(['matchId', 'eventSec'])

    # Prepare passes
    passes_sorted = passes_df[['matchId', 'eventSec', 'playerId', 'teamId', 'end_x', 'end_y']].copy()
    passes_sorted = passes_sorted.sort_values(['matchId', 'eventSec'])

    receiver_ids = pd.Series(index=passes_sorted.index, dtype='object')

    # Process by match for efficiency
    for match_id in tqdm(passes_sorted['matchId'].unique(), desc="  Finding receivers", leave=False):
        match_passes = passes_sorted[passes_sorted['matchId'] == match_id]
        match_events = events_sorted[events_sorted['matchId'] == match_id]

        for idx, pass_row in match_passes.iterrows():
            # Find candidate receivers: same team, different player, after pass
            candidates = match_events[
                (match_events['eventSec'] > pass_row['eventSec']) &
                (match_events['eventSec'] <= pass_row['eventSec'] + time_threshold) &
                (match_events['teamId'] == pass_row['teamId']) &
                (match_events['playerId'] != pass_row['playerId'])
            ]

            if len(candidates) == 0:
                receiver_ids.loc[idx] = None
                continue

            # Calculate spatial distance from pass endpoint
            distances = np.sqrt(
                (candidates['start_x'] - pass_row['end_x'])**2 +
                (candidates['start_y'] - pass_row['end_y'])**2
            )

            # Find closest valid receiver
            valid_mask = distances <= distance_threshold
            if valid_mask.any():
                closest_idx = distances[valid_mask].idxmin()
                receiver_ids.loc[idx] = candidates.loc[closest_idx, 'playerId']
            else:
                receiver_ids.loc[idx] = None

    return receiver_ids.reindex(passes_df.index)


def process_competition_events(
    events: List[dict],
    competition_name: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process events from a single competition.
    
    Args:
        events: List of event dictionaries
        competition_name: Name of the competition
        
    Returns:
        Tuple of (pass_network_df, statistics_dict)
    """
    logger.info(f"Processing {competition_name}...")
    
    # Convert to DataFrame
    df_events = pd.DataFrame(events)
    
    # Filter pass events
    df_passes = df_events[df_events['eventId'] == PASS_EVENT_ID].copy()
    
    if len(df_passes) == 0:
        logger.warning(f"No passes found in {competition_name}")
        return pd.DataFrame(), {}
    
    # Mark accurate passes
    df_passes['accurate'] = df_passes['tags'].apply(
        lambda x: any(tag['id'] == ACCURATE_TAG_ID for tag in x) if isinstance(x, list) else False
    )
    
    # Extract positions
    position_data = df_passes.apply(extract_positions, axis=1)
    df_passes = pd.concat([df_passes, position_data], axis=1)
    df_passes_clean = df_passes.dropna(subset=['start_x', 'start_y', 'end_x', 'end_y']).copy()
    
    # Calculate pass metrics
    df_passes_clean['pass_distance'] = np.sqrt(
        (df_passes_clean['end_x'] - df_passes_clean['start_x'])**2 + 
        (df_passes_clean['end_y'] - df_passes_clean['start_y'])**2
    )
    df_passes_clean['pass_angle'] = np.arctan2(
        df_passes_clean['end_y'] - df_passes_clean['start_y'],
        df_passes_clean['end_x'] - df_passes_clean['start_x']
    ) * 180 / np.pi
    
    # Extract start positions for all events
    df_events[['start_x', 'start_y']] = df_events['positions'].apply(
        lambda x: pd.Series(extract_start_position(x))
    )
    
    # Filter accurate passes only
    df_passes_accurate = df_passes_clean[df_passes_clean['accurate'] == True].copy()
    
    # Ensure numeric types
    df_events['eventSec'] = pd.to_numeric(df_events['eventSec'], errors='coerce')
    df_passes_accurate['eventSec'] = pd.to_numeric(df_passes_accurate['eventSec'], errors='coerce')
    
    # Find receivers
    df_passes_accurate['passer_id'] = df_passes_accurate['playerId']
    df_passes_accurate['receiver_id'] = find_receivers_vectorized(df_passes_accurate, df_events)
    
    # Remove passes without receiver
    df_passes_network = df_passes_accurate.dropna(subset=['receiver_id']).copy()
    
    # Add competition identifier
    df_passes_network['competition'] = competition_name
    
    # Statistics
    stats = {
        'total_passes': len(df_passes),
        'accurate_passes': len(df_passes_accurate),
        'passes_with_receiver': len(df_passes_network),
        'accuracy_rate': len(df_passes_accurate) / len(df_passes) * 100 if len(df_passes) > 0 else 0,
        'receiver_identification_rate': len(df_passes_network) / len(df_passes_accurate) * 100 if len(df_passes_accurate) > 0 else 0
    }
    
    logger.info(f"  {stats['total_passes']:,} passes | "
                f"{stats['accurate_passes']:,} accurate | "
                f"{stats['passes_with_receiver']:,} with receiver")
    
    return df_passes_network, stats


# ============================================================================
# NETWORK CONSTRUCTION
# ============================================================================

def aggregate_pass_connections(all_passes: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate pass connections across all competitions.
    
    Args:
        all_passes: DataFrame containing all passes from all competitions
        
    Returns:
        DataFrame of aggregated pass connections with metrics
    """
    logger.info("Aggregating pass connections...")
    
    # Group by passer-receiver pairs
    pass_connections = all_passes.groupby(['passer_id', 'receiver_id']).agg({
        'accurate': 'mean',
        'pass_distance': 'mean',
        'pass_angle': 'mean',
        'competition': lambda x: list(x.unique())  # List of competitions where connection occurs
    }).reset_index()
    
    # Add pass counts
    pass_connections['pass_count'] = all_passes.groupby(['passer_id', 'receiver_id']).size().values
    
    # Count number of competitions
    pass_connections['num_competitions'] = pass_connections['competition'].apply(len)
    
    # Rename columns
    pass_connections = pass_connections.rename(columns={
        'accurate': 'accuracy',
        'pass_distance': 'avg_pass_distance',
        'pass_angle': 'avg_pass_angle',
        'competition': 'competitions_list'
    })
    
    logger.info(f"Created {len(pass_connections):,} unique pass connections")
    
    return pass_connections


def create_player_nodes(
    pass_connections: pd.DataFrame,
    df_players: pd.DataFrame,
    df_teams: pd.DataFrame,
    all_passes: pd.DataFrame
) -> pd.DataFrame:
    """
    Create player nodes with enriched attributes.
    
    Args:
        pass_connections: DataFrame of pass connections
        df_players: DataFrame of player information
        df_teams: DataFrame of team information
        all_passes: DataFrame of all passes for calculating per-player statistics
        
    Returns:
        DataFrame of player nodes with attributes
    """
    logger.info("Creating player nodes...")
    
    # Get unique players
    players_involved = set(pass_connections['passer_id']).union(set(pass_connections['receiver_id']))
    players_involved = {pid for pid in players_involved if pid > 0}  # Filter invalid IDs
    
    players_involved_df = pd.DataFrame(list(players_involved), columns=['player_id'])
    logger.info(f"  {len(players_involved_df):,} unique players across all competitions")
    
    # Merge with player database
    player_nodes = players_involved_df.merge(
        df_players[['passportArea', 'currentTeamId', 'weight', 'birthDate', 
                    'height', 'role', 'wyId', 'foot', 'shortName', 'currentNationalTeamId']], 
        left_on='player_id', 
        right_on='wyId', 
        how='left'
    ).merge(
        df_teams[['wyId', 'name']].rename(columns={'wyId': 'currentTeamId', 'name': 'current_team_name'}),
        on='currentTeamId',
        how='left'
    )
    
    # Rename columns
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
    
    # Handle missing player data
    missing_data_mask = player_nodes['player_name'].isna()
    if missing_data_mask.any():
        missing_count = missing_data_mask.sum()
        logger.warning(f"  {missing_count} players not found in database - creating placeholders")
        player_nodes.loc[missing_data_mask, 'player_name'] = player_nodes.loc[missing_data_mask, 'player_id'].apply(
            lambda x: f"Unknown_Player_{int(x)}"
        )
    
    # Extract nested dictionary values
    player_nodes['passport_area'] = player_nodes['passport_area'].apply(
        lambda d: d.get('name') if isinstance(d, dict) else d
    )
    player_nodes['position_role'] = player_nodes['position_role'].apply(
        lambda d: d.get('name') if isinstance(d, dict) else d
    )
    
    # Calculate per-player statistics from pass data
    logger.info("  Calculating player statistics...")
    
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
    
    # Merge statistics
    player_nodes = player_nodes.merge(
        player_stats, left_on='player_id', right_index=True, how='left'
    ).merge(
        receiver_stats, left_on='player_id', right_index=True, how='left'
    )
    
    # Fill NaN values with defaults
    player_nodes = player_nodes.fillna({
        'weight_kg': 0,
        'height_cm': 0,
        'birth_date': '',
        'passport_area': 'Unknown',
        'position_role': 'Unknown',
        'preferred_foot': 'Unknown',
        'current_team_name': 'Unknown',
        'national_team_id': 0,
        'currentTeamId': 0,
        'avg_pass_distance': 0.0,
        'std_pass_distance': 0.0,
        'pass_accuracy': 0.0,
        'num_competitions': 0,
        'total_passes_made': 0,
        'avg_pass_distance_received': 0.0,
        'total_passes_received': 0
    })
    
    # Drop the competitions_played list (too complex for some formats)
    player_nodes = player_nodes.drop(columns=['competitions_played'], errors='ignore')
    
    # Set index and clean up
    player_nodes = player_nodes.set_index('player_id')
    player_nodes = player_nodes.drop(columns=['wyId'], errors='ignore')
    
    # Ensure correct data types
    numeric_cols = ['weight_kg', 'height_cm', 'national_team_id', 'currentTeamId', 
                    'num_competitions', 'total_passes_made', 'total_passes_received']
    for col in numeric_cols:
        if col in player_nodes.columns:
            player_nodes[col] = pd.to_numeric(player_nodes[col], errors='coerce').fillna(0).astype(int)
    
    float_cols = ['avg_pass_distance', 'std_pass_distance', 'pass_accuracy', 'avg_pass_distance_received']
    for col in float_cols:
        if col in player_nodes.columns:
            player_nodes[col] = pd.to_numeric(player_nodes[col], errors='coerce').fillna(0.0).astype(float)
    
    logger.info(f"Player nodes created with {len(player_nodes.columns)} attributes")
    
    return player_nodes


def build_unified_network(
    pass_connections: pd.DataFrame,
    player_nodes: pd.DataFrame
) -> nx.DiGraph:
    """
    Build unified directed network graph.
    
    Args:
        pass_connections: DataFrame of pass connections
        player_nodes: DataFrame of player nodes with attributes
        
    Returns:
        NetworkX DiGraph
    """
    logger.info("Building unified network graph...")
    
    G = nx.DiGraph()
    
    # Add nodes with attributes
    for pid, attrs in player_nodes.iterrows():
        node_attrs = attrs.to_dict()
        node_attrs['label'] = node_attrs.get('player_name', str(pid))
        G.add_node(int(pid), **node_attrs)
    
    logger.info(f"  Added {G.number_of_nodes():,} nodes")
    
    # Add edges
    edges_added = 0
    edges_skipped = 0
    
    for _, row in pass_connections.iterrows():
        s = int(row['passer_id'])
        t = int(row['receiver_id'])
        
        # Skip invalid IDs
        if s <= 0 or t <= 0:
            edges_skipped += 1
            continue
        
        # Only add edges between valid nodes
        if s in player_nodes.index and t in player_nodes.index:
            # Prepare edge attributes
            edge_attrs = {
                'pass_count': int(row['pass_count']),
                'accuracy': float(row['accuracy']),
                'avg_pass_distance': float(row['avg_pass_distance']),
                'avg_pass_angle': float(row['avg_pass_angle']),
                'num_competitions': int(row['num_competitions']),
                'weight': int(row['pass_count'])  # For visualization
            }
            
            # Convert competitions list to string for compatibility
            if 'competitions_list' in row:
                edge_attrs['competitions'] = ', '.join(row['competitions_list'])
            
            G.add_edge(s, t, **edge_attrs)
            edges_added += 1
        else:
            edges_skipped += 1
    
    logger.info(f"  Added {G.number_of_edges():,} edges")
    if edges_skipped > 0:
        logger.warning(f"  Skipped {edges_skipped} edges (invalid nodes)")
    
    return G


# ============================================================================
# NETWORK ANALYSIS & METRICS
# ============================================================================

def calculate_network_metrics(G: nx.DiGraph) -> Dict:
    """
    Calculate comprehensive network metrics.
    
    Args:
        G: NetworkX DiGraph
        
    Returns:
        Dictionary of network metrics
    """
    logger.info("Calculating network metrics...")
    
    metrics = {
        'num_nodes': G.number_of_nodes(),
        'num_edges': G.number_of_edges(),
        'density': nx.density(G),
        'avg_in_degree': sum(d for n, d in G.in_degree()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
        'avg_out_degree': sum(d for n, d in G.out_degree()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
    }
    
    # Degree distribution
    in_degrees = [d for n, d in G.in_degree()]
    out_degrees = [d for n, d in G.out_degree()]
    
    metrics['max_in_degree'] = max(in_degrees) if in_degrees else 0
    metrics['max_out_degree'] = max(out_degrees) if out_degrees else 0
    metrics['std_in_degree'] = np.std(in_degrees) if in_degrees else 0
    metrics['std_out_degree'] = np.std(out_degrees) if out_degrees else 0
    
    # Connectivity
    if nx.is_weakly_connected(G):
        metrics['weakly_connected'] = True
        metrics['num_weakly_connected_components'] = 1
    else:
        metrics['weakly_connected'] = False
        metrics['num_weakly_connected_components'] = nx.number_weakly_connected_components(G)
    
    # Largest component
    largest_wcc = max(nx.weakly_connected_components(G), key=len)
    metrics['largest_component_size'] = len(largest_wcc)
    metrics['largest_component_pct'] = len(largest_wcc) / G.number_of_nodes() * 100 if G.number_of_nodes() > 0 else 0
    
    logger.info("Metrics calculated successfully")
    
    return metrics


def print_network_summary(metrics: Dict, competition_stats: Dict):
    """Print comprehensive network summary."""
    logger.info("\n" + "="*80)
    logger.info("UNIFIED PASS NETWORK SUMMARY")
    logger.info("="*80)
    
    logger.info("\nCOMPETITION COVERAGE:")
    logger.info(f"Competitions processed: {len(competition_stats)}")
    total_passes = sum(s['total_passes'] for s in competition_stats.values())
    total_accurate = sum(s['accurate_passes'] for s in competition_stats.values())
    total_with_receiver = sum(s['passes_with_receiver'] for s in competition_stats.values())
    logger.info(f"Total passes: {total_passes:,}")
    logger.info(f"Accurate passes: {total_accurate:,} ({total_accurate/total_passes*100:.1f}%)")
    logger.info(f"Passes with receiver: {total_with_receiver:,} ({total_with_receiver/total_accurate*100:.1f}%)")
    
    logger.info("\nNETWORK STRUCTURE:")
    logger.info(f"Nodes (players): {metrics['num_nodes']:,}")
    logger.info(f"Edges (connections): {metrics['num_edges']:,}")
    logger.info(f"Network density: {metrics['density']:.6f}")
    logger.info(f"Average in-degree: {metrics['avg_in_degree']:.2f}")
    logger.info(f"Average out-degree: {metrics['avg_out_degree']:.2f}")
    
    logger.info("\nCONNECTIVITY:")
    logger.info(f"Weakly connected: {metrics['weakly_connected']}")
    logger.info(f"Connected components: {metrics['num_weakly_connected_components']}")
    logger.info(f"Largest component: {metrics['largest_component_size']:,} nodes "
                f"({metrics['largest_component_pct']:.1f}%)")
    
    logger.info("\nDEGREE STATISTICS:")
    logger.info(f"Max in-degree: {metrics['max_in_degree']}")
    logger.info(f"Max out-degree: {metrics['max_out_degree']}")
    logger.info(f"Std in-degree: {metrics['std_in_degree']:.2f}")
    logger.info(f"Std out-degree: {metrics['std_out_degree']:.2f}")
    
    logger.info("="*80 + "\n")


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def export_network(G: nx.DiGraph, base_filename: str):
    """
    Export network in multiple formats.
    
    Args:
        G: NetworkX DiGraph
        base_filename: Base filename without extension
        formats: List of formats to export
    """
    logger.info("Exporting unified network...")

    try:
        output_path = NETWORKS_DIR / base_filename
        
        filepath = f"{output_path}.gexf"
        nx.write_gexf(G, filepath)
        logger.info(f"GEXF: {filepath}")
                
        
    except Exception as e:
        logger.error(f"Failed to export network: {e}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    start_time = datetime.now()
    logger.info("="*80)
    logger.info("UNIFIED PASS NETWORK GENERATOR")
    logger.info("="*80)
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Ensure output directory exists
    NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load reference data
    logger.info("Loading reference data...")
    players = load_json_fixed(DATA_DIR / "players.json")
    teams = load_json_fixed(DATA_DIR / "teams.json")
    
    df_players = pd.DataFrame(players)
    df_teams = pd.DataFrame(teams)
    
    logger.info(f"Loaded {len(df_players):,} players")
    logger.info(f"Loaded {len(df_teams):,} teams\n")
    
    # Get all event files
    event_files = sorted(list(EVENTS_DIR.glob("events_*.json")))
    logger.info(f"Found {len(event_files)} competition event files\n")
    
    # Process all competitions
    all_passes_list = []
    competition_stats = {}
    
    for event_file in tqdm(event_files, desc="Processing competitions", unit="file"):
        competition_name = event_file.stem.replace('events_', '')
        
        try:
            # Load events
            events = load_json_fixed(event_file)
            
            # Process competition
            passes_df, stats = process_competition_events(events, competition_name)
            
            if len(passes_df) > 0:
                all_passes_list.append(passes_df)
                competition_stats[competition_name] = stats
            
        except Exception as e:
            logger.error(f"Error processing {competition_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    if not all_passes_list:
        logger.error("No valid pass data found across all competitions!")
        return
    
    # Combine all passes
    logger.info("\nCombining data from all competitions...")
    all_passes = pd.concat(all_passes_list, ignore_index=True)
    logger.info(f"Total passes across all competitions: {len(all_passes):,}")
    
    # Aggregate pass connections
    pass_connections = aggregate_pass_connections(all_passes)
    
    # Create player nodes with statistics
    player_nodes = create_player_nodes(pass_connections, df_players, df_teams, all_passes)
    
    # Build unified network
    G = build_unified_network(pass_connections, player_nodes)
    
    # Calculate metrics
    metrics = calculate_network_metrics(G)
    
    # Print summary
    print_network_summary(metrics, competition_stats)
    
    # Export network
    export_network(G, 'pass_network_unified')
    
    # Final summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("\n" + "="*80)
    logger.info("GENERATION COMPLETE")
    logger.info("="*80)
    logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Duration: {duration}")
    logger.info(f"Log file: {log_file}")
    logger.info("="*80)


if __name__ == "__main__":
    main()
