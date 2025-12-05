"""
Centralized Configuration
=========================
All constants, paths, and configuration parameters in one place.
"""

from pathlib import Path
from typing import Dict
import multiprocessing as mp


# ============================================================================
# DIRECTORY PATHS
# ============================================================================

# Base directories
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
LOG_DIR = PROJECT_ROOT / 'logs'
NETWORKS_DIR = DATA_DIR / 'Networks'

# Data subdirectories
EVENTS_DIR = DATA_DIR / 'events'
MATCHES_DIR = DATA_DIR / 'matches'

# Network output subdirectories
PASS_NETWORKS_DIR = NETWORKS_DIR / 'passes'
MATCH_NETWORKS_DIR = NETWORKS_DIR / 'matches'
PLAYER_TEAM_NETWORKS_DIR = NETWORKS_DIR / 'player_team'


# ============================================================================
# DATA FILE PATHS
# ============================================================================

PLAYERS_FILE = DATA_DIR / 'players.json'
TEAMS_FILE = DATA_DIR / 'teams.json'
COMPETITIONS_FILE = DATA_DIR / 'competitions.json'
EVENT_ID_MAP_FILE = DATA_DIR / 'eventid2name.csv'


# ============================================================================
# EVENT IDS AND TAGS
# ============================================================================

# Event type IDs
PASS_EVENT_ID = 8
DUEL_EVENT_ID = 1
SHOT_EVENT_ID = 10
FOUL_EVENT_ID = 2
FREE_KICK_EVENT_ID = 3
TACKLE_EVENT_ID = 4

# Tag IDs
ACCURATE_TAG_ID = 1801
ASSIST_TAG_ID = 301
KEY_PASS_TAG_ID = 302
THROUGH_BALL_TAG_ID = 1901


# ============================================================================
# NETWORK GENERATION PARAMETERS
# ============================================================================

# Pass network parameters
DISTANCE_THRESHOLD = 5.0  # Maximum distance to identify receiver (units)
TIME_THRESHOLD = 5.0      # Maximum time window to identify receiver (seconds)

# Performance tuning
MAX_WORKERS = max(1, mp.cpu_count() - 1)  # Leave one core free
BATCH_SIZE = 1000  # Batch size for vectorized operations


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

class LogConfig:
    """Logging configuration settings."""
    
    # Default log level (can be overridden)
    DEFAULT_LEVEL = 'INFO'  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # Log file settings
    ENABLE_FILE_LOGGING = True
    ENABLE_CONSOLE_LOGGING = True
    
    # Log format
    SIMPLE_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    
    # Which external libraries to silence
    SILENCE_EXTERNAL_LOGGERS = True
    EXTERNAL_LOGGERS = ['matplotlib', 'urllib3', 'PIL', 'networkx']


# ============================================================================
# NETWORK EXPORT SETTINGS
# ============================================================================

class ExportConfig:
    """Network export configuration."""
    
    # Default export format
    DEFAULT_FORMAT = 'gexf'  # Options: gexf, graphml, gml, pajek
    
    # Export multiple formats
    EXPORT_FORMATS = ['gexf']  # Can add more: ['gexf', 'graphml']
    
    # Compression
    COMPRESS_OUTPUTS = False


# ============================================================================
# COMPETITION NAMES
# ============================================================================

COMPETITIONS = [
    'England',
    'European_Championship',
    'France',
    'Germany',
    'Italy',
    'Spain',
    'World_Cup'
]


# ============================================================================
# VALIDATION SETTINGS
# ============================================================================

class ValidationConfig:
    """Data validation settings."""
    
    # Minimum thresholds
    MIN_PLAYERS_PER_MATCH = 10
    MIN_PASSES_PER_MATCH = 50
    
    # Quality checks
    VALIDATE_PLAYER_IDS = True
    VALIDATE_TEAM_IDS = True
    REMOVE_INVALID_NODES = True


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_competition_events_file(competition: str) -> Path:
    """Get events file path for a competition."""
    return EVENTS_DIR / f"events_{competition}.json"


def get_competition_matches_file(competition: str) -> Path:
    """Get matches file path for a competition."""
    return MATCHES_DIR / f"matches_{competition}.json"


def ensure_directories():
    """Create all necessary directories if they don't exist."""
    directories = [
        LOG_DIR,
        NETWORKS_DIR,
        PASS_NETWORKS_DIR,
        MATCH_NETWORKS_DIR,
        PLAYER_TEAM_NETWORKS_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_settings_dict() -> Dict:
    """Get all settings as a dictionary for logging/debugging."""
    return {
        'data_dir': str(DATA_DIR),
        'log_dir': str(LOG_DIR),
        'distance_threshold': DISTANCE_THRESHOLD,
        'time_threshold': TIME_THRESHOLD,
        'max_workers': MAX_WORKERS,
        'pass_event_id': PASS_EVENT_ID,
        'accurate_tag_id': ACCURATE_TAG_ID,
        'log_level': LogConfig.DEFAULT_LEVEL,
        'export_format': ExportConfig.DEFAULT_FORMAT,
    }


# Ensure directories exist on import
ensure_directories()
