"""
Data Loading and Processing Utilities
======================================
Reusable functions for data manipulation, JSON loading, and position extraction.
"""

import json
from pathlib import Path
from typing import Tuple, Optional, Union
import pandas as pd
import numpy as np


def fix_unicode_escapes(obj):
    """
    Recursively decode \\uXXXX sequences in all strings.
    
    Args:
        obj: Object to process (str, list, dict, or other)
        
    Returns:
        Object with unicode escapes fixed
    """
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


def load_json_fixed(path: Union[str, Path]):
    """
    Load JSON file with automatic unicode escape fixing.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Loaded and processed JSON data
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return fix_unicode_escapes(data)


def extract_positions(row: pd.Series) -> pd.Series:
    """
    Extract start and end positions from event data (single row).
    
    Args:
        row: DataFrame row containing 'positions' field
        
    Returns:
        Series with start_x, start_y, end_x, end_y
    """
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


def extract_positions_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    """
    Vectorized position extraction - much faster than apply() for large datasets.
    
    Args:
        df: DataFrame with 'positions' column
        
    Returns:
        DataFrame with start_x, start_y, end_x, end_y columns
    """
    positions = df['positions'].values
    n = len(positions)
    
    # Pre-allocate arrays
    start_x = np.full(n, np.nan)
    start_y = np.full(n, np.nan)
    end_x = np.full(n, np.nan)
    end_y = np.full(n, np.nan)
    
    # Vectorized extraction
    for i, pos in enumerate(positions):
        if isinstance(pos, list) and len(pos) >= 2:
            start_x[i] = pos[0].get('x', np.nan)
            start_y[i] = pos[0].get('y', np.nan)
            end_x[i] = pos[1].get('x', np.nan)
            end_y[i] = pos[1].get('y', np.nan)
    
    return pd.DataFrame({
        'start_x': start_x,
        'start_y': start_y,
        'end_x': end_x,
        'end_y': end_y
    }, index=df.index)


def extract_start_positions_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract only start positions (for events that don't have end positions).
    
    Args:
        df: DataFrame with 'positions' column
        
    Returns:
        DataFrame with start_x, start_y columns
    """
    positions = df['positions'].values
    n = len(positions)
    
    start_x = np.full(n, np.nan)
    start_y = np.full(n, np.nan)
    
    for i, pos in enumerate(positions):
        if isinstance(pos, list) and len(pos) > 0:
            start_x[i] = pos[0].get('x', np.nan)
            start_y[i] = pos[0].get('y', np.nan)
    
    return pd.DataFrame({'start_x': start_x, 'start_y': start_y}, index=df.index)


def extract_start_position(positions) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract start x,y from positions array (for use with apply).
    
    Args:
        positions: List of position dictionaries
        
    Returns:
        Tuple of (x, y) or (None, None)
    """
    if positions and len(positions) > 0:
        return positions[0].get('x'), positions[0].get('y')
    return None, None
