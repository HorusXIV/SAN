# LE3 Figures - GEPHI Visualization Guide

This directory should contain the following figures generated in GEPHI:

## Required Figures

### 1. Pass Network Visualizations
Source file: `data/Networks/passes/pass_network_Germany.gexf`

- **pass_network_full.png**: Complete pass network
  - Layout: ForceAtlas2
  - Node size: by degree centrality
  - Node color: by team
  - Edge width: by pass_count
  - Labels: top 20 nodes by degree

- **pass_network_filtered.png**: Filtered network (weight ≥ 10 passes)
  - Same styling as above
  - Shows backbone structure

- **pass_network_kcore.png**: 10-core subgraph
  - Node color: by betweenness centrality
  - Highlights dense core

### 2. Match Network Visualizations
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

### 3. Bipartite Network Visualization
Source file: `data/Networks/player_team/player_team_network_Germany.gexf`

- **bipartite_network.png**: Two-mode visualization
  - Layout: Bipartite (players left, teams right)
  - Node color: by type (players=blue, teams=orange)
  - Node size: by connection count
  - Edge width: by matches_together

### 4. Projection Network Visualization
Source: Export from LE3.ipynb (G_player_projection)

- **player_projection_network.png**: Player-player projection
  - Layout: ForceAtlas2
  - Node size: by degree
  - Edge width: by weight
  - Community detection coloring

## Export Settings

All figures should use:
- **Resolution**: 300 DPI minimum
- **Format**: PNG with transparent background
- **Dimensions**: ~2000x1500 pixels
- **Font**: Arial or similar sans-serif, 12pt minimum

## GEPHI Import Notes

1. Open GEPHI
2. File → Open → Select .gexf file
3. Import report: Ensure all attributes are recognized
4. Apply layout algorithm
5. Configure appearance (nodes, edges, labels)
6. Preview and export

## Filtering in GEPHI

For filtered networks (e.g., pass_network_filtered.png):
1. Filters → Attributes → Range → weight
2. Set minimum to 10
3. Filter → Apply
4. Generate layout on filtered network
