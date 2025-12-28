# LE3 Figures - GEPHI Visualization Guide

This directory should contain the following figures generated in GEPHI:


## 1. Pass Network Visualizations
Source file: `data/Networks/passes/pass_network_Germany.gexf`

- **pass_network_full.png**: Complete pass network
  - Layout: OpenOrd
  - Node size: by degree centrality
  - Node color: by team
  - Edge width: by pass_count
  - Labels: top nodes by degree

- **pass_network_filtered.png**: Filtered network (weight ≥ 25 passes)
  - Same styling as above
  - Shows backbone structure

- **pass_network_kcore.png**: 20-core subgraph
  - Node color: by betweenness centrality
  - Highlights dense core

## 2. Match Network Visualizations
Source file: `data/Networks/matches/match_network_World_Cup.gexf`

- **match_network_circular.png**: Circular layout
  - Layout: Circular
  - Node size: by total_matches
  - Node color: by goal_difference (gradient red→green)
  - Edge width: by weight
  - Curved edges

- **match_network_hierarchical.png**: Hierarchical layout
  - Layout: Hierarchical (by goal_difference)
  - Shows tournament structure

## 3. Bipartite Network Visualization
Source file: `data/Networks/player_team/player_team_network_Germany.gexf`

- **bipartite_network.png**: Two-mode visualization
  - Layout: Bipartite (players left, teams right)
  - Node color: by type (players=blue, teams=orange)
  - Node size: by connection count
  - Edge width: by matches_together

## 4. Projection Network Visualization
Source: Export from LE3.ipynb (G_player_projection)

- **player_projection_network.png**: Player-player projection
  - Layout: ForceAtlas2
  - Node size: by degree
  - Edge width: by weight
  - Community detection coloring