# Soccer Network Analysis (SAN)

Network analysis of professional soccer match data using spatio-temporal event data from multiple European competitions and international tournaments.

## Authors

- Lukas Breiter
- Gian Truttmann
- Jessica Schmid

## Overview

This project applies social network analysis techniques to professional soccer data, generating and analyzing multiple network types:

- **Pass Networks**: Directed player-to-player networks based on passing interactions
- **Match Networks**: Team-to-team networks representing competitive relationships
- **Player-Team Networks**: Bipartite networks capturing player-team affiliations
- **Field Networks**: Spatial networks representing field zone interactions
- **Unified Networks**: Aggregated cross-competition networks

The analysis includes centrality metrics, community detection, k-core decomposition, and temporal network evolution studies.

## Project Structure

```
.
├── data/                          # Raw and processed data
│   ├── events/                    # Match event data by competition
│   ├── matches/                   # Match metadata and results
│   ├── Networks/                  # Generated network files (GEXF)
│   │   ├── passes/               # Pass networks
│   │   ├── matches/              # Match networks
│   │   ├── player_team/          # Bipartite networks
│   │   └── field/                # Field zone networks
│   └── *.json                    # Players, teams, competitions data
├── src/                          # Source code
│   ├── common/                   # Shared utilities
│   │   ├── data_utils.py        # JSON loading, position extraction
│   │   ├── network_utils.py     # KD-tree receiver detection
│   │   └── logging_config.py    # Centralized logging
│   ├── config/                   # Configuration
│   │   └── settings.py          # Paths, parameters, constants
│   └── network_generators/       # Network generation modules
│       ├── pass_networks.py     # Player pass networks
│       ├── match_networks.py    # Team match networks
│       ├── player_team_networks.py  # Bipartite networks
│       ├── field_networks.py    # Field zone networks
│       └── unified_pass_network.py  # Cross-competition unified network
├── Notebooks/                    # Analysis notebooks
│   ├── EDA.ipynb                # Exploratory data analysis
│   ├── LE3.ipynb - LE10.ipynb   # Learning exercise notebooks
│   └── pass_network.gexf        # Sample network for analysis
├── reports/                      # LaTeX report and figures
│   ├── SAN_bericht.tex          # Main report
│   ├── figures/                 # Generated figures
│   ├── sections/                # Report sections
│   └── literature/              # Bibliography
├── logs/                         # Execution logs
├── pyproject.toml               # Poetry configuration
└── poetry.lock                  # Locked dependencies
```

## Features

### Network Generation
- **Optimized receiver detection** using KD-tree spatial indexing (O(log n) queries)
- **Vectorized operations** for large-scale data processing
- **Parallel processing** with weighted progress tracking
- **Rich node attributes**: player demographics, roles, team affiliations
- **Edge weights**: pass counts, accuracy, distance, angles
- **Built-in metrics**: centrality, community detection, k-core

### Network Analysis
- Centrality metrics (degree, betweenness, closeness, PageRank)
- Community detection (Louvain, label propagation, greedy modularity, Girvan-Newman)
- K-core decomposition
- Network projections (bipartite → one-mode)
- Temporal evolution analysis

## Data Source

**Primary Dataset:**
Pappalardo, L., Cintia, P., Rossi, A. et al. (2019). *A public data set of spatio-temporal match events in soccer competitions*. Scientific Data, 6, 236. https://doi.org/10.1038/s41597-019-0247-7

**Data Repository:**
Pappalardo, L., & Massucco, E. (2019). *Soccer match event dataset* (Version 5). figshare. https://doi.org/10.6084/m9.figshare.c.4415000.v5

**Competitions Included:**
- English Premier League
- Spanish La Liga
- German Bundesliga
- Italian Serie A
- French Ligue 1
- UEFA European Championship
- FIFA World Cup

## Requirements

- Python 3.12+
- Poetry 2.0+

### Core Dependencies
| Package | Purpose |
|---------|---------|
| networkx | Graph construction and analysis |
| pandas, numpy | Data processing |
| scipy | KD-tree spatial indexing |
| matplotlib, seaborn | Visualization |
| tqdm | Progress tracking |
| gensim | Network embeddings |
| scikit-learn | Machine learning utilities |

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd SAN

# Install dependencies with Poetry
poetry install

# Activate the virtual environment
poetry shell
```

## Usage

### Generate Networks

All network generators are executed as Python modules via Poetry:

```bash
# Generate pass networks for all competitions
poetry run python -m src.network_generators.pass_networks

# Generate match networks
poetry run python -m src.network_generators.match_networks

# Generate player-team bipartite networks
poetry run python -m src.network_generators.player_team_networks

# Generate field zone networks
poetry run python -m src.network_generators.field_networks

# Generate unified cross-competition network
poetry run python -m src.network_generators.unified_pass_network
```

### Run Notebooks

```bash
# Start Jupyter notebook server
poetry run jupyter notebook

# Or use JupyterLab
poetry run jupyter lab
```

### Quick Start (All Networks)

```bash
# Generate all network types
poetry run python -m src.network_generators.pass_networks && \
poetry run python -m src.network_generators.match_networks && \
poetry run python -m src.network_generators.player_team_networks && \
poetry run python -m src.network_generators.field_networks && \
poetry run python -m src.network_generators.unified_pass_network
```

## Output

Generated networks are saved in GEXF format (compatible with Gephi) under `data/Networks/`:

| Directory | Contents |
|-----------|----------|
| `passes/` | `pass_network_{competition}.gexf` |
| `matches/` | `match_network_{competition}.gexf` |
| `player_team/` | `player_team_network_{competition}.gexf` |
| `field/` | `field_network_{competition}.gexf` |

## Development

### Add Dependencies

```bash
# Add a production dependency
poetry add <package-name>

# Add a development dependency
poetry add --group dev <package-name>
```

### Code Style

The project follows PEP 8 conventions. Key patterns:
- Type hints for function signatures
- Docstrings for public functions
- Vectorized operations over loops where possible

## Related Work

This project builds upon methodologies from:

- **Network science in sports**: Grund (2012), "Network structure and team performance"
- **Pass network analysis**: Clemente et al. (2015), "Using network metrics to investigate football team players' connections"
- **Spatio-temporal analysis**: Bialkowski et al. (2014), "Identifying team style in soccer using formations learned from spatiotemporal tracking data"
- **Social network analysis**: Wasserman & Faust (1994), "Social Network Analysis: Methods and Applications"

## License

Academic use only. Original data licensed under CC BY 4.0.
