"""
Centralized Configuration
=========================
All constants, paths, and configuration parameters in one place.
"""

from pathlib import Path
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
FIELD_NETWORKS_DIR = NETWORKS_DIR / 'field'


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
SHOT_EVENT_ID = 10
FREE_KICK_EVENT_ID = 3

# Tag IDs
ACCURATE_TAG_ID = 1801  # Successful pass
UNSUCCESSFUL_TAG_ID = 1802  # Unsuccessful pass
INTERCEPTION_TAG_ID = 1401  # Pass intercepted
ASSIST_TAG_ID = 301
KEY_PASS_TAG_ID = 302
THROUGH_BALL_TAG_ID = 1901


# ============================================================================
# NETWORK GENERATION PARAMETERS
# ============================================================================

# Pass network parameters
DISTANCE_THRESHOLD = 5.0  # Maximum distance to identify receiver (units)
TIME_THRESHOLD = 10.0

# Performance tuning
MAX_WORKERS = max(1, mp.cpu_count() - 1)  # Leave one core free


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
# HELPER FUNCTIONS
# ============================================================================

def get_competition_events_file(competition: str) -> Path:
    """Get events file path for a competition."""
    return EVENTS_DIR / f"events_{competition}.json"


def get_competition_matches_file(competition: str) -> Path:
    """Get matches file path for a competition."""
    return MATCHES_DIR / f"matches_{competition}.json"


def _ensure_directories():
    """Create all necessary directories if they don't exist (internal)."""
    for directory in [LOG_DIR, NETWORKS_DIR, PASS_NETWORKS_DIR, 
                      MATCH_NETWORKS_DIR, PLAYER_TEAM_NETWORKS_DIR, FIELD_NETWORKS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# Ensure directories exist on import
_ensure_directories()