"""Configuration package."""

from .settings import (
    # Directories
    DATA_DIR,
    LOG_DIR,
    NETWORKS_DIR,
    EVENTS_DIR,
    MATCHES_DIR,
    PASS_NETWORKS_DIR,
    MATCH_NETWORKS_DIR,
    PLAYER_TEAM_NETWORKS_DIR,
    
    # Files
    PLAYERS_FILE,
    TEAMS_FILE,
    
    # Event IDs
    PASS_EVENT_ID,
    ACCURATE_TAG_ID,
    
    # Parameters
    DISTANCE_THRESHOLD,
    TIME_THRESHOLD,
    MAX_WORKERS,
    
    # Config classes
    LogConfig,
    ExportConfig,
    ValidationConfig,
    
    # Helper functions
    get_competition_events_file,
    get_competition_matches_file,
    ensure_directories,
    get_settings_dict,
)

__all__ = [
    'DATA_DIR',
    'LOG_DIR',
    'NETWORKS_DIR',
    'EVENTS_DIR',
    'MATCHES_DIR',
    'PASS_NETWORKS_DIR',
    'MATCH_NETWORKS_DIR',
    'PLAYER_TEAM_NETWORKS_DIR',
    'PLAYERS_FILE',
    'TEAMS_FILE',
    'PASS_EVENT_ID',
    'ACCURATE_TAG_ID',
    'DISTANCE_THRESHOLD',
    'TIME_THRESHOLD',
    'MAX_WORKERS',
    'LogConfig',
    'ExportConfig',
    'ValidationConfig',
    'get_competition_events_file',
    'get_competition_matches_file',
    'ensure_directories',
    'get_settings_dict',
]
