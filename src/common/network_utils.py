"""
Network Analysis Utilities
==========================
Shared functions for network construction, analysis, and metrics calculation.
"""

import networkx as nx
import pandas as pd
import numpy as np
from typing import Dict, Optional
from collections import defaultdict
from scipy.spatial import cKDTree
from tqdm.auto import tqdm


def find_receivers_kdtree(passes_df: pd.DataFrame, events_df: pd.DataFrame, 
                          distance_threshold: float = 5.0, time_threshold: float = 3.0) -> pd.Series:
    """
    Find pass receivers using KD-Tree spatial indexing for optimal performance.
    
    Uses scipy's cKDTree for O(log n) nearest neighbor queries, providing
    50-100x speedup over nested loop approaches.
    
    For successful passes: finds receiver from the same team
    For intercepted passes: finds receiver from the opposing team
    For unsuccessful passes: finds next player to touch ball (any team)
    
    Args:
        passes_df: DataFrame containing pass events with columns:
                   matchId, eventSec, playerId, teamId, end_x, end_y, pass_type
        events_df: DataFrame containing all events with columns:
                   matchId, eventSec, playerId, teamId, start_x, start_y
        distance_threshold: Maximum distance (in units) between pass end and next event
        time_threshold: Maximum time (in seconds) after pass to find receiver
        
    Returns:
        Series of receiver player IDs indexed by pass DataFrame index
    """
    receiver_ids = pd.Series(index=passes_df.index, dtype='Int64')
    
    events_clean = events_df[['matchId', 'eventSec', 'playerId', 'teamId', 'start_x', 'start_y']].dropna()
    passes_clean = passes_df[['matchId', 'eventSec', 'playerId', 'teamId', 'end_x', 'end_y', 'pass_type']].dropna(subset=['matchId', 'eventSec', 'playerId', 'teamId', 'end_x', 'end_y'])
    
    for match_id in tqdm(passes_clean['matchId'].unique(), desc="Finding receivers", 
                         position=1, leave=False):
        match_passes = passes_clean[passes_clean['matchId'] == match_id]
        match_events = events_clean[events_clean['matchId'] == match_id]
        
        if len(match_events) == 0:
            continue
        
        # Build KD-Tree for spatial queries
        event_coords = match_events[['start_x', 'start_y']].values
        tree = cKDTree(event_coords)
        
        # Query nearest neighbors for all passes at once
        pass_coords = match_passes[['end_x', 'end_y']].values
        distances, indices = tree.query(pass_coords, k=min(10, len(match_events)), 
                                        distance_upper_bound=distance_threshold)
        
        # Filter candidates by temporal and team constraints
        for i, (pass_idx, pass_row) in enumerate(match_passes.iterrows()):
            candidate_indices = indices[i]
            candidate_distances = distances[i]
            
            # Filter out infinite distances (no neighbors within threshold)
            valid_mask = np.isfinite(candidate_distances)
            if not valid_mask.any():
                receiver_ids.loc[pass_idx] = pd.NA
                continue
            
            candidate_indices = candidate_indices[valid_mask]
            candidates = match_events.iloc[candidate_indices]
            
            # Apply temporal and player constraints
            time_mask = (
                (candidates['eventSec'] > pass_row['eventSec']) &
                (candidates['eventSec'] <= pass_row['eventSec'] + time_threshold)
            )
            player_mask = (candidates['playerId'] != pass_row['playerId'])
            
            # Team constraint depends on pass type:
            # - successful: receiver from same team
            # - intercepted: receiver from opposing team
            # - unsuccessful: next player to touch ball (any team)
            pass_type = pass_row.get('pass_type', 'successful')
            if pass_type == 'intercepted':
                team_mask = (candidates['teamId'] != pass_row['teamId'])  # Opposing team
            elif pass_type == 'unsuccessful':
                team_mask = pd.Series([True] * len(candidates), index=candidates.index)  # Any team
            else:
                team_mask = (candidates['teamId'] == pass_row['teamId'])  # Same team
            
            valid_receivers = candidates[time_mask & team_mask & player_mask]
            
            if len(valid_receivers) > 0:
                receiver_ids.loc[pass_idx] = valid_receivers.iloc[0]['playerId']
            else:
                receiver_ids.loc[pass_idx] = pd.NA
    
    return receiver_ids


def calculate_network_metrics(G: nx.Graph, directed: bool = True) -> Dict:
    """
    Calculate comprehensive network metrics.
    
    Args:
        G: NetworkX Graph or DiGraph
        directed: Whether graph is directed
        
    Returns:
        Dictionary of network metrics
    """
    metrics = {
        'num_nodes': G.number_of_nodes(),
        'num_edges': G.number_of_edges(),
        'density': nx.density(G) if G.number_of_nodes() > 0 else 0
    }
    
    if directed and isinstance(G, nx.DiGraph):
        in_degrees = [d for n, d in G.in_degree()]
        out_degrees = [d for n, d in G.out_degree()]
        
        metrics['avg_in_degree'] = sum(in_degrees) / len(in_degrees) if in_degrees else 0
        metrics['avg_out_degree'] = sum(out_degrees) / len(out_degrees) if out_degrees else 0
        metrics['max_in_degree'] = max(in_degrees) if in_degrees else 0
        metrics['max_out_degree'] = max(out_degrees) if out_degrees else 0
        
        # Connectivity for directed graphs
        if G.number_of_nodes() > 0:
            metrics['weakly_connected'] = nx.is_weakly_connected(G)
            metrics['num_weakly_connected_components'] = nx.number_weakly_connected_components(G)
            
            if metrics['num_weakly_connected_components'] > 0:
                largest_wcc = max(nx.weakly_connected_components(G), key=len)
                metrics['largest_component_size'] = len(largest_wcc)
                metrics['largest_component_pct'] = len(largest_wcc) / G.number_of_nodes() * 100
    else:
        degrees = [d for n, d in G.degree()]
        metrics['avg_degree'] = sum(degrees) / len(degrees) if degrees else 0
        metrics['max_degree'] = max(degrees) if degrees else 0
        
        # Connectivity for undirected graphs
        if G.number_of_nodes() > 0:
            metrics['connected'] = nx.is_connected(G)
            metrics['num_connected_components'] = nx.number_connected_components(G)
    
    return metrics
