"""
Field Network Generator
=======================
Generates spatial field networks where nodes represent field locations
and edges represent event sequences between locations.

The network captures the flow of play across the field, with focus on
ball-contact events: Passes, Shots, and Free Kicks.
"""

from pathlib import Path
from tqdm.auto import tqdm
import pandas as pd
import numpy as np
import networkx as nx
from typing import Optional, Tuple
from datetime import datetime
from collections import defaultdict

from src.common import load_json_fixed
from src.config import (
    DATA_DIR,
    EVENTS_DIR,
    NETWORKS_DIR,
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
                        df_teams: pd.DataFrame, competition_name: str) -> nx.MultiDiGraph:
    """
    Create a field network from events.
    
    Nodes represent field locations (discretized into grid cells).
    Edges represent event sequences between locations.
    
    Args:
        events: List of event dictionaries
        df_players: DataFrame with player information
        df_teams: DataFrame with team information
        competition_name: Name of the competition
        
    Returns:
        NetworkX MultiDiGraph representing the field network
    """
    G = nx.MultiDiGraph()
    
    # Filter for ball-contact events: Pass, Shot, Free Kick
    relevant_event_ids = [PASS_EVENT_ID, SHOT_EVENT_ID, FREE_KICK_EVENT_ID]
    
    df_events = pd.DataFrame(events)
    df_filtered = df_events[df_events['eventId'].isin(relevant_event_ids)].copy()
    
    # Sort by match, period, and time
    df_filtered = df_filtered.sort_values(['matchId', 'matchPeriod', 'eventSec'])
    
    print(f"Processing {len(df_filtered)} ball-contact events...")
    
    # Track node statistics
    node_event_counts = defaultdict(int)
    node_event_types = defaultdict(lambda: defaultdict(int))
    node_player_counts = defaultdict(set)
    node_team_counts = defaultdict(set)
    
    # Process events to create edges
    edge_data = []
    
    for idx, event in tqdm(df_filtered.iterrows(), total=len(df_filtered), 
                          desc="Building field network"):
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
        node_player_counts[loc_id_start].add(event['playerId'])
        node_team_counts[loc_id_start].add(event['teamId'])
        
        # If event has an end location, create edge
        if end_loc is not None:
            x_end, y_end = end_loc
            if not (pd.isna(x_end) or pd.isna(y_end)):
                grid_end = discretize_location(x_end, y_end)
                loc_id_end = create_location_id(*grid_end)
                
                # Update node statistics for end location
                node_event_counts[loc_id_end] += 1
                node_event_types[loc_id_end][event['eventName']] += 1
                
                # Create edge
                edge_data.append({
                    'source': loc_id_start,
                    'target': loc_id_end,
                    'event_type': event['eventName'],
                    'sub_event_type': event.get('subEventName', ''),
                    'player_id': event['playerId'],
                    'team_id': event['teamId'],
                    'match_id': event['matchId'],
                    'match_period': event['matchPeriod'],
                    'event_sec': event['eventSec'],
                    'start_x': x_start,
                    'start_y': y_start,
                    'end_x': x_end,
                    'end_y': y_end
                })
    
    # Add nodes with attributes
    print(f"Adding {len(node_event_counts)} location nodes...")
    for loc_id in node_event_counts.keys():
        # Parse coordinates from location ID
        parts = loc_id.split('_')
        x, y = int(parts[1]), int(parts[2])
        
        # Calculate node statistics
        total_events = node_event_counts[loc_id]
        event_type_dist = dict(node_event_types[loc_id])
        unique_players = len(node_player_counts[loc_id])
        unique_teams = len(node_team_counts[loc_id])
        
        # Dominant event type
        dominant_event = max(event_type_dist.items(), key=lambda x: x[1])[0] if event_type_dist else ''
        
        G.add_node(
            loc_id,
            x=x,
            y=y,
            center_x=x + GRID_SIZE / 2,  # Center of grid cell
            center_y=y + GRID_SIZE / 2,
            total_events=total_events,
            unique_players=unique_players,
            unique_teams=unique_teams,
            dominant_event_type=dominant_event,
            pass_count=event_type_dist.get('Pass', 0),
            shot_count=event_type_dist.get('Shot', 0),
            free_kick_count=event_type_dist.get('Free Kick', 0),
            event_type_distribution=str(event_type_dist)
        )
    
    # Add edges
    print(f"Adding {len(edge_data)} edges...")
    for edge in tqdm(edge_data, desc="Adding edges"):
        G.add_edge(
            edge['source'],
            edge['target'],
            event_type=edge['event_type'],
            sub_event_type=edge['sub_event_type'],
            player_id=edge['player_id'],
            team_id=edge['team_id'],
            match_id=edge['match_id'],
            match_period=edge['match_period'],
            event_sec=edge['event_sec'],
            start_x=edge['start_x'],
            start_y=edge['start_y'],
            end_x=edge['end_x'],
            end_y=edge['end_y'],
            distance=np.sqrt((edge['end_x'] - edge['start_x'])**2 + 
                           (edge['end_y'] - edge['start_y'])**2)
        )
    
    # Add graph metadata
    G.graph['competition'] = competition_name
    G.graph['network_type'] = 'field_location'
    G.graph['grid_size'] = GRID_SIZE
    G.graph['event_types'] = ['Pass', 'Shot', 'Free Kick']
    G.graph['created'] = datetime.now().isoformat()
    
    print(f"Field network created: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    return G


def process_competition(competition_name: str, output_dir: Path) -> None:
    """
    Process a single competition and generate field network.
    
    Args:
        competition_name: Name of the competition
        output_dir: Directory to save the network
    """
    print(f"\n{'='*70}")
    print(f"Processing: {competition_name}")
    print(f"{'='*70}")
    
    # Load events
    events_file = EVENTS_DIR / f"events_{competition_name}.json"
    if not events_file.exists():
        print(f"⚠️  Events file not found: {events_file}")
        return
    
    print(f"Loading events from {events_file}...")
    events = load_json_fixed(events_file)
    print(f"Loaded {len(events)} events")
    
    # Load players and teams
    df_players = pd.DataFrame(load_json_fixed(PLAYERS_FILE))
    df_teams = pd.DataFrame(load_json_fixed(TEAMS_FILE))
    
    # Create network
    G = create_field_network(events, df_players, df_teams, competition_name)
    
    # Save network
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"field_network_{competition_name}.gexf"
    nx.write_gexf(G, output_file)
    print(f"✓ Saved to {output_file}")
    
    # Print statistics
    print(f"\n{'='*70}")
    print(f"Network Statistics for {competition_name}:")
    print(f"{'='*70}")
    print(f"Nodes (Locations): {G.number_of_nodes()}")
    print(f"Edges (Event Sequences): {G.number_of_edges()}")
    print(f"Average Degree: {sum(dict(G.degree()).values()) / G.number_of_nodes():.2f}")
    print(f"Network Density: {nx.density(G):.6f}")
    
    # Top active locations
    node_activity = [(node, data['total_events']) 
                     for node, data in G.nodes(data=True)]
    node_activity.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\nTop 5 Most Active Locations:")
    for i, (node, events) in enumerate(node_activity[:5], 1):
        data = G.nodes[node]
        print(f"  {i}. {node} - {events} events "
              f"(x={data['center_x']:.1f}, y={data['center_y']:.1f})")


def main():
    """Main function to generate field networks for all competitions."""
    print("="*70)
    print("FIELD NETWORK GENERATOR")
    print("="*70)
    print(f"Grid Size: {GRID_SIZE}x{GRID_SIZE}")
    print(f"Event Types: Pass, Shot, Free Kick")
    print("="*70)
    
    # Define output directory
    output_dir = NETWORKS_DIR / 'field'
    
    # Use predefined competition list
    competition_names = COMPETITIONS
    
    print(f"\nFound {len(competition_names)} competitions")
    print(f"Output directory: {output_dir}")
    
    # Process each competition
    for comp_name in competition_names:
        try:
            process_competition(comp_name, output_dir)
        except Exception as e:
            print(f"❌ Error processing {comp_name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("FIELD NETWORK GENERATION COMPLETE")
    print("="*70)


if __name__ == '__main__':
    main()
