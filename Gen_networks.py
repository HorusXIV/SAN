import json
from pathlib import Path
from tqdm.auto import tqdm
import pandas as pd
import numpy as np
import networkx as nx
from typing import Optional, Dict, Set
import logging
from datetime import datetime


# Configuration
DATA_DIR = Path('data')
EVENTS_DIR = DATA_DIR / 'events'
NETWORKS_DIR = DATA_DIR / 'Networks'
PASS_EVENT_ID = 8
ACCURATE_TAG_ID = 1801

# Setup logging
log_file = DATA_DIR / f'network_generation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


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


def load_json_fixed(path):
    """Load JSON file with unicode escape fix."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return fix_unicode_escapes(data)


def extract_positions(row):
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


def extract_start_position(positions):
    """Extract start x,y from positions array."""
    if positions and len(positions) > 0:
        return positions[0].get('x'), positions[0].get('y')
    return None, None


def find_receivers_vectorized(passes_df, events_df, distance_threshold=5.0, time_threshold=5.0):
    """Find pass receivers using vectorized approach."""
    events_sorted = events_df[['matchId', 'eventSec', 'playerId', 'teamId', 'start_x', 'start_y']].copy()
    events_sorted = events_sorted.dropna(subset=['start_x', 'start_y'])
    events_sorted = events_sorted.sort_values(['matchId', 'eventSec'])

    passes_sorted = passes_df[['matchId', 'eventSec', 'playerId', 'teamId', 'end_x', 'end_y']].copy()
    passes_sorted = passes_sorted.sort_values(['matchId', 'eventSec'])

    receiver_ids = pd.Series(index=passes_sorted.index, dtype='object')

    for match_id in tqdm(passes_sorted['matchId'].unique(), desc="  Finding receivers", leave=False):
        match_passes = passes_sorted[passes_sorted['matchId'] == match_id]
        match_events = events_sorted[events_sorted['matchId'] == match_id]

        for idx, pass_row in match_passes.iterrows():
            candidates = match_events[
                (match_events['eventSec'] > pass_row['eventSec']) &
                (match_events['eventSec'] <= pass_row['eventSec'] + time_threshold) &
                (match_events['teamId'] == pass_row['teamId']) &
                (match_events['playerId'] != pass_row['playerId'])
            ]

            if len(candidates) == 0:
                receiver_ids.loc[idx] = None
                continue

            distances = np.sqrt(
                (candidates['start_x'] - pass_row['end_x'])**2 +
                (candidates['start_y'] - pass_row['end_y'])**2
            )

            valid_mask = distances <= distance_threshold
            if valid_mask.any():
                closest_idx = distances[valid_mask].idxmin()
                receiver_ids.loc[idx] = candidates.loc[closest_idx, 'playerId']
            else:
                receiver_ids.loc[idx] = None

    return receiver_ids.reindex(passes_df.index)


def validate_player_data(player_ids: Set[int], df_players: pd.DataFrame) -> Dict:
    """
    Validate player IDs against the players database.
    Returns statistics about coverage.
    """
    valid_player_ids = set(df_players['wyId'].values)
    missing_ids = player_ids - valid_player_ids
    
    # Remove invalid IDs (0 or negative)
    invalid_ids = {pid for pid in player_ids if pid <= 0}
    
    return {
        'total_players': len(player_ids),
        'valid_players': len(player_ids & valid_player_ids),
        'missing_players': len(missing_ids - invalid_ids),
        'invalid_players': len(invalid_ids),
        'missing_ids': sorted(list(missing_ids - invalid_ids)),
        'invalid_ids': sorted(list(invalid_ids)),
        'coverage_pct': (len(player_ids & valid_player_ids) / len(player_ids) * 100) if player_ids else 0
    }


def create_pass_network(events, df_players, df_teams, competition_name):
    """
    Create a pass network from events data with improved data handling.
    """
    logger.info(f"Processing {competition_name}...")
    
    # Convert to DataFrame
    df_events = pd.DataFrame(events)
    
    # Filter pass events    
    df_passes = df_events[df_events['eventId'] == PASS_EVENT_ID].copy()
    
    if len(df_passes) == 0:
        logger.warning(f"No passes found in {competition_name}, skipping...")
        return None
    
    logger.info(f"Total pass events: {len(df_passes):,}")
    
    # Mark accurate passes
    df_passes['accurate'] = df_passes['tags'].apply(
        lambda x: any(tag['id'] == ACCURATE_TAG_ID for tag in x) if isinstance(x, list) else False
    )
    
    # Extract positions for passes
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
    
    # Filter accurate passes
    df_passes_accurate = df_passes_clean[df_passes_clean['accurate'] == True].copy()
    
    # Ensure numeric types
    df_events['eventSec'] = pd.to_numeric(df_events['eventSec'], errors='coerce')
    df_passes_accurate['eventSec'] = pd.to_numeric(df_passes_accurate['eventSec'], errors='coerce')
    
    # Find receivers
    df_passes_accurate['passer_id'] = df_passes_accurate['playerId']
    df_passes_accurate['receiver_id'] = find_receivers_vectorized(df_passes_accurate, df_events)
    
    # Remove passes without receiver
    df_passes_network = df_passes_accurate.dropna(subset=['receiver_id'])
    
    logger.info(f"  Passes with receiver: {len(df_passes_network)} ({len(df_passes_network)/len(df_passes_accurate)*100:.1f}%)")
    
    if len(df_passes_network) == 0:
        logger.warning(f"No passes with receivers found in {competition_name}, skipping...")
        return None
    
    # Create pass connections
    pass_connections = df_passes_network.groupby(['passer_id', 'receiver_id']).agg({
        'accurate': 'mean',
        'pass_distance': 'mean',
        'pass_angle': 'mean'
    }).reset_index()
    pass_connections['pass_count'] = df_passes_network.groupby(['passer_id', 'receiver_id']).size().values
    pass_connections = pass_connections.rename(columns={
        'accurate': 'accuracy',
        'pass_distance': 'avg_pass_distance',
        'pass_angle': 'avg_pass_angle'
    })
    
    # Get players involved
    players_involved = set(pass_connections['passer_id']).union(set(pass_connections['receiver_id']))
    
    # CRITICAL FIX: Filter out invalid player IDs BEFORE merge
    players_involved = {pid for pid in players_involved if pid > 0}
    
    players_involved_df = pd.DataFrame(list(players_involved), columns=['player_id'])
    logger.info(f"Unique players involved in passes: {len(players_involved_df)}")
    
    # Validate player data
    validation_stats = validate_player_data(players_involved, df_players)
    logger.info(f"  Player data validation:")
    logger.info(f"    - Valid players: {validation_stats['valid_players']}")
    logger.info(f"    - Missing from DB: {validation_stats['missing_players']}")
    logger.info(f"    - Invalid IDs: {validation_stats['invalid_players']}")
    logger.info(f"    - Coverage: {validation_stats['coverage_pct']:.2f}%")
    
    if validation_stats['missing_ids']:
        logger.warning(f"Missing player IDs: {validation_stats['missing_ids'][:10]}")
    
    # CRITICAL FIX: Use LEFT join to preserve all players, then handle missing data
    player_nodes = players_involved_df.merge(
        df_players[['passportArea', 'currentTeamId', 'weight', 'birthDate', 
                    'height', 'role', 'wyId', 'foot', 'shortName', 'currentNationalTeamId']], 
        left_on='player_id', 
        right_on='wyId', 
        how='left'  # CHANGED FROM 'inner' TO 'left'
    ).merge(
        df_teams[['wyId', 'name']].rename(columns={'wyId': 'currentTeamId', 'name': 'current_team_name'}),
        on='currentTeamId',
        how='left'
    )
    
    logger.info(f"Players after merge: {len(player_nodes)}")
    
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
    
    # IMPROVED: Handle missing player data gracefully
    # For players not found in database, create placeholder attributes
    missing_data_mask = player_nodes['player_name'].isna()
    if missing_data_mask.any():
        missing_count = missing_data_mask.sum()
        logger.warning(f"Creating placeholder data for {missing_count} players not found in database")
        player_nodes.loc[missing_data_mask, 'player_name'] = player_nodes.loc[missing_data_mask, 'player_id'].apply(
            lambda x: f"Unknown_Player_{int(x)}"
        )
    
    # Set index
    player_nodes = player_nodes.set_index('player_id')
    player_nodes = player_nodes.drop(columns=['wyId'], errors='ignore')
    
    # Extract nested dict values
    player_nodes['passport_area'] = player_nodes['passport_area'].apply(
        lambda d: d.get('name') if isinstance(d, dict) else d
    )
    player_nodes['position_role'] = player_nodes['position_role'].apply(
        lambda d: d.get('name') if isinstance(d, dict) else d
    )
    
    # Fill NaN values with appropriate defaults
    player_nodes = player_nodes.fillna({
        'weight_kg': 0,
        'height_cm': 0,
        'birth_date': '',
        'passport_area': 'Unknown',
        'position_role': 'Unknown',
        'preferred_foot': 'Unknown',
        'current_team_name': 'Unknown',
        'national_team_id': 0,
        'currentTeamId': 0
    })
    
    # Fill any remaining NaN and ensure correct data types
    for col in player_nodes.columns:
        if player_nodes[col].dtype == 'object':
            player_nodes[col] = player_nodes[col].fillna('Unknown')
        else:
            player_nodes[col] = player_nodes[col].fillna(0)
    
    # Ensure numeric columns are proper integers (not floats or strings)
    numeric_cols = ['weight_kg', 'height_cm', 'national_team_id', 'currentTeamId']
    for col in numeric_cols:
        if col in player_nodes.columns:
            player_nodes[col] = pd.to_numeric(player_nodes[col], errors='coerce').fillna(0).astype(int)
    
    # Create network graph
    G = nx.DiGraph()
    
    # Add nodes with attributes
    for pid, attrs in player_nodes.iterrows():
        node_attrs = attrs.to_dict()
        node_attrs['label'] = node_attrs.get('player_name', str(pid))
        G.add_node(int(pid), **node_attrs)
    
    # Add edges (only between valid nodes)
    edges_added = 0
    edges_skipped = 0
    for _, row in pass_connections.iterrows():
        s = row['passer_id']
        t = row['receiver_id']
        
        # Skip invalid player IDs
        if s <= 0 or t <= 0:
            edges_skipped += 1
            continue
        
        if s in player_nodes.index and t in player_nodes.index:
            G.add_edge(int(s), int(t), 
                       pass_count=int(row['pass_count']),
                       accuracy=float(row['accuracy']),
                       avg_pass_distance=float(row['avg_pass_distance']),
                       avg_pass_angle=float(row['avg_pass_angle']))
            edges_added += 1
        else:
            edges_skipped += 1
    
    logger.info(f"  Network created: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    if edges_skipped > 0:
        logger.info(f"  Skipped {edges_skipped} edges (invalid or missing players)")
    
    return G


def main():
    """Main function to process all event files and create networks."""
    
    # Ensure output directory exists
    NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load reference data
    logger.info("Loading reference data...")
    players = load_json_fixed(DATA_DIR / "players.json")
    teams = load_json_fixed(DATA_DIR / "teams.json")
    
    df_players = pd.DataFrame(players)
    df_teams = pd.DataFrame(teams)
    
    logger.info(f"  Loaded {len(df_players):,} players")
    logger.info(f"  Loaded {len(df_teams):,} teams")
    
    # Get all event files
    event_files = list(EVENTS_DIR.glob("events_*.json"))
    logger.info(f"\nFound {len(event_files)} event files to process\n")
    
    # Process each event file
    success_count = 0
    fail_count = 0
    
    for event_file in tqdm(event_files, desc="Overall progress", unit="file"):
        competition_name = event_file.stem.replace('events_', '')
        
        try:
            # Load events
            events = load_json_fixed(event_file)
            
            # Create network
            G = create_pass_network(events, df_players, df_teams, competition_name)
            
            if G is not None:
                # Save network
                output_file = NETWORKS_DIR / f"pass_network_{competition_name}.gexf"
                nx.write_gexf(G, output_file)
                logger.info(f"Saved to {output_file}\n")
                success_count += 1
            else:
                fail_count += 1
                
        except Exception as e:
            logger.error(f" Error processing {competition_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            fail_count += 1
    
    logger.info("\n" + "="*80)
    logger.info(f"GENERATION COMPLETE")
    logger.info(f"  Successful: {success_count}/{len(event_files)}")
    logger.info(f"  Failed: {fail_count}/{len(event_files)}")
    logger.info(f"  Log file: {log_file}")
    logger.info("="*80)


if __name__ == "__main__":
    main()
