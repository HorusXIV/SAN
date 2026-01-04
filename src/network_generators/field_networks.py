"""
Field Network Generator
Generates spatial field networks where nodes represent field locations
and edges represent event sequences between locations.
"""

from tqdm.auto import tqdm
import pandas as pd
import numpy as np
import networkx as nx
from typing import Optional, Tuple
from datetime import datetime
from collections import defaultdict

from src.common import load_json_fixed
from src.config import (
    EVENTS_DIR,
    FIELD_NETWORKS_DIR,
    PLAYERS_FILE,
    TEAMS_FILE,
    PASS_EVENT_ID,
    SHOT_EVENT_ID,
    FREE_KICK_EVENT_ID,
    COMPETITIONS
)


# Field dimensions (Wyscout coordinates: 0-100 for both x and y)
FIELD_WIDTH = 100
FIELD_HEIGHT = 100

# Spatial discretization - create grid cells for location nodes
GRID_SIZE = 5  # 5x5 meter grid cells (adjust for desired granularity)


def discretize_location(x: float, y: float, grid_size: int = GRID_SIZE) -> Tuple[int, int]:
    """
    Discretize continuous field coordinates to grid cells.
    
    Args:
        x: X coordinate (0-100)
        y: Y coordinate (0-100)
        grid_size: Size of grid cells
        
    Returns:
        Tuple of (grid_x, grid_y) representing the cell
    """
    grid_x = int(x // grid_size) * grid_size
    grid_y = int(y // grid_size) * grid_size
    return (grid_x, grid_y)


def create_location_id(x: int, y: int) -> str:
    """Create unique location ID from grid coordinates."""
    return f"loc_{x}_{y}"


def extract_location_from_event(event: dict) -> Optional[Tuple[float, float]]:
    """
    Extract starting location from event.
    
    Args:
        event: Event dictionary
        
    Returns:
        Tuple of (x, y) coordinates or None if not available
    """
    positions = event.get('positions', [])
    if positions and len(positions) > 0:
        pos = positions[0]  # First position is the starting location
        return (pos.get('x'), pos.get('y'))
    return None


def extract_end_location_from_event(event: dict) -> Optional[Tuple[float, float]]:
    """
    Extract end location from event (for passes, shots, etc.).
    
    Args:
        event: Event dictionary
        
    Returns:
        Tuple of (x, y) coordinates or None if not available
    """
    positions = event.get('positions', [])
    if positions and len(positions) > 1:
        pos = positions[1]  # Second position is the end location
        return (pos.get('x'), pos.get('y'))
    return None


def create_field_network(events: list, df_players: pd.DataFrame, 
                        df_teams: pd.DataFrame, competition_name: str) -> nx.DiGraph:
    """
    Create an aggregated field network from events.
    
    Nodes represent field locations (discretized into grid cells).
    Edges represent aggregated event flows between locations.
    
    Args:
        events: List of event dictionaries
        df_players: DataFrame with player information
        df_teams: DataFrame with team information
        competition_name: Name of the competition
        
    Returns:
        NetworkX DiGraph representing the aggregated field network
    """
    G = nx.DiGraph()
    
    # Filter for ball-contact events: Pass, Shot, Free Kick
    relevant_event_ids = [PASS_EVENT_ID, SHOT_EVENT_ID, FREE_KICK_EVENT_ID]
    
    df_events = pd.DataFrame(events)
    df_filtered = df_events[df_events['eventId'].isin(relevant_event_ids)].copy()
    df_filtered = df_filtered.sort_values(['matchId', 'matchPeriod', 'eventSec'])
    
    # Track node statistics
    node_event_counts = defaultdict(int)
    node_event_types = defaultdict(lambda: defaultdict(int))
    
    # Track edges: (source, target, event_type) -> count
    edge_aggregation = defaultdict(lambda: defaultdict(int))
    
    for idx, event in df_filtered.iterrows():
        # Extract locations
        start_loc = extract_location_from_event(event)
        end_loc = extract_end_location_from_event(event)
        
        if start_loc is None:
            continue
            
        x_start, y_start = start_loc
        if pd.isna(x_start) or pd.isna(y_start):
            continue
            
        # Discretize start location
        grid_start = discretize_location(x_start, y_start)
        loc_id_start = create_location_id(*grid_start)
        
        # Update node statistics for start location
        node_event_counts[loc_id_start] += 1
        node_event_types[loc_id_start][event['eventName']] += 1
        
        # If event has an end location, aggregate edge
        if end_loc is not None:
            x_end, y_end = end_loc
            if not (pd.isna(x_end) or pd.isna(y_end)):
                grid_end = discretize_location(x_end, y_end)
                loc_id_end = create_location_id(*grid_end)
                
                # Update node statistics for end location
                node_event_counts[loc_id_end] += 1
                node_event_types[loc_id_end][event['eventName']] += 1
                
                # Aggregate edge by event type
                edge_key = (loc_id_start, loc_id_end)
                event_type = event['eventName']
                edge_aggregation[edge_key][event_type] += 1
    
    # Add nodes with attributes
    for loc_id in node_event_counts.keys():
        parts = loc_id.split('_')
        x, y = int(parts[1]), int(parts[2])
        
        total_events = node_event_counts[loc_id]
        event_type_dist = dict(node_event_types[loc_id])
        dominant_event = max(event_type_dist.items(), key=lambda x: x[1])[0] if event_type_dist else ''
        
        G.add_node(
            loc_id,
            x=x,
            y=y,
            center_x=x + GRID_SIZE / 2,
            center_y=y + GRID_SIZE / 2,
            total_events=total_events,
            dominant_event_type=dominant_event,
            pass_count=event_type_dist.get('Pass', 0),
            shot_count=event_type_dist.get('Shot', 0),
            free_kick_count=event_type_dist.get('Free Kick', 0)
        )
    
    # Add aggregated edges
    for (source, target), event_type_counts in edge_aggregation.items():
        for event_type, count in event_type_counts.items():
            source_data = G.nodes[source]
            target_data = G.nodes[target]
            distance = np.sqrt((target_data['center_x'] - source_data['center_x'])**2 + 
                             (target_data['center_y'] - source_data['center_y'])**2)
            
            G.add_edge(
                source,
                target,
                key=event_type,
                event_type=event_type,
                weight=count,
                distance=distance
            )
    
    G.graph['competition'] = competition_name
    G.graph['network_type'] = 'field_location_aggregated'
    G.graph['grid_size'] = GRID_SIZE
    G.graph['event_types'] = ['Pass', 'Shot', 'Free Kick']
    G.graph['created'] = datetime.now().isoformat()
    
    return G


def process_competition(competition_name: str) -> Tuple[str, str, Optional[str]]:
    """
    Process a single competition and generate field network.
    
    Args:
        competition_name: Name of the competition
        
    Returns:
        Tuple of (competition_name, status, result)
    """
    events_file = EVENTS_DIR / f"events_{competition_name}.json"
    if not events_file.exists():
        return (competition_name, 'no_data', None)
    
    try:
        events = load_json_fixed(events_file)
        df_players = pd.DataFrame(load_json_fixed(PLAYERS_FILE))
        df_teams = pd.DataFrame(load_json_fixed(TEAMS_FILE))
        
        G = create_field_network(events, df_players, df_teams, competition_name)
        
        FIELD_NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
        output_file = FIELD_NETWORKS_DIR / f"field_network_{competition_name}.gexf"
        nx.write_gexf(G, output_file)
        
        return (competition_name, 'success', str(output_file))
        
    except Exception as e:
        return (competition_name, 'error', str(e))


def main():
    """Main execution function for field network generation."""
    start_time = datetime.now()
    tqdm.write(f"Starting field network generation (Grid: {GRID_SIZE}x{GRID_SIZE})")
    
    results = []
    for comp_name in tqdm(COMPETITIONS, desc="Processing competitions"):
        result = process_competition(comp_name)
        results.append(result)
        
        if result[1] == 'error':
            tqdm.write(f"Error processing {comp_name}: {result[2]}")
    
    success_count = sum(1 for r in results if r[1] == 'success')
    fail_count = len(results) - success_count
    
    duration = datetime.now() - start_time
    tqdm.write(f"Complete: {success_count} successful, {fail_count} failed in {duration}")


if __name__ == '__main__':
    main()
