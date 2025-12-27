# Soccer Network Analysis (SAN)

Network analysis of professional soccer match data using spatio-temporal event data from multiple European competitions and international tournaments.

## Authors

- Lukas Breiter
- GianTruttman
- Jessica Schmied

## Overview

This project applies social network analysis techniques to professional soccer data, generating and analyzing multiple network types:

- **Pass Networks**: Directed player-to-player networks based on passing interactions
- **Match Networks**: Team-to-team networks representing competitive relationships
- **Player-Team Networks**: Bipartite networks capturing player-team affiliations
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
│   │   └── player_team/          # Bipartite networks
│   └── *.json                    # Players, teams, competitions data
├── src/                          # Source code
│   ├── common/                   # Shared utilities
│   │   ├── data_utils.py        # JSON loading, position extraction
│   │   ├── network_utils.py     # Network analysis, KD-tree receiver detection
│   │   └── logging_config.py    # Centralized logging
│   ├── config/                   # Configuration
│   │   └── settings.py          # Paths, parameters, constants
│   └── network_generators/       # Network generation modules
│       ├── pass_networks.py
│       ├── match_networks.py
│       ├── player_team_networks.py
│       └── unified_pass_network.py
├── Notebooks/                    # Analysis notebooks
│   ├── EDA.ipynb                # Exploratory data analysis
│   ├── LE3.ipynb                # Network modeling & filtering
│   ├── LE4.ipynb                # Centrality & community detection
│   └── LE5.ipynb                # Network projections & dynamics
└── reports/                      # LaTeX report and figures
```

## Features

### Network Generation
- **Optimized receiver detection** using KD-tree spatial indexing
- **Vectorized operations** for large-scale data processing
- **Parallel processing** for multi-competition analysis
- **Rich node attributes**: player demographics, roles, team affiliations
- **Edge weights**: pass counts, accuracy, distance, angles

### Network Analysis
- Centrality metrics (degree, betweenness, closeness, eigenvector)
- Community detection (Louvain, label propagation, greedy modularity)
- K-core decomposition
- Network projections (bipartite → one-mode)
- Temporal evolution analysis

## Data Source

**Primary Dataset:**
Pappalardo, L., Cintia, P., Rossi, A. et al. (2019). *A public data set of spatio-temporal match events in soccer competitions*. Scientific Data, 6, 236. https://doi.org/10.1038/s41597-019-0247-7

**Data Repository:**
Pappalardo, L., & Massucco, E. (2019). *Soccer match event dataset* (Version 5). figshare. https://doi.org/10.6084/m9.figshare.c.4415000.v5

The dataset includes event-level data from:
- English Premier League
- Spanish La Liga
- German Bundesliga
- Italian Serie A
- French Ligue 1
- UEFA European Championship
- FIFA World Cup

## Requirements

- Python 3.12+
- NetworkX 3.6+
- pandas, numpy, scipy
- matplotlib, seaborn
- tqdm, ijson
- gensim, tensorflow (for embeddings)
- fastdtw (for time series analysis)

Install dependencies:
```bash
pip install -e .
```

## Usage

Generate networks:
```python
# Pass networks
python -m src.network_generators.pass_networks

# Match networks
python -m src.network_generators.match_networks

# Player-team networks
python -m src.network_generators.player_team_networks

# Unified network
python -m src.network_generators.unified_pass_network
```

## Related Work

This project builds upon methodologies from:

- **Network science in sports**: Grund (2012), "Network structure and team performance"
- **Pass network analysis**: Clemente et al. (2015), "Using network metrics to investigate football team players' connections"
- **Spatio-temporal analysis**: Bialkowski et al. (2014), "Identifying team style in soccer using formations learned from spatiotemporal tracking data"
- **Social network analysis**: Wasserman & Faust (1994), "Social Network Analysis: Methods and Applications"

## License

Academic use only. Original data licensed under CC BY 4.0.
