# LE4 Figures - Community Detection Visualizations

This directory contains the following community detection visualizations generated in GEPHI:

## Required Figures

### 1. Pass Network Community Visualizations
Source file: `data/Networks/passes/pass_network_Germany.gexf`

**pass_communities_louvain.png**: Main community visualization
- Layout: ForceAtlas2 with Prevent Overlap
- Node color: By community (use Louvain modularity class attribute)
- Node size: By degree
- Edge: Light gray, low opacity (0.2)
- Labels: Show for nodes with degree > 20
- Color palette: Use distinct colors for each of the 11 communities

**pass_communities_algorithm_comparison.png**: Side-by-side comparison (2x2 grid)
- Create 4 subplots showing Louvain, Label Propagation, Greedy, Girvan-Newman
- Same layout and styling for fair comparison

**pass_community_largest.png**: Zoom into largest communitiy
- Extract largest communities
- Node labels visible for all players

### 2. Match Network Community Visualization
Source file: `data/Networks/matches/match_network_World_Cup.gexf`

**match_communities_louvain.png**: World Cup tournament communities
- Layout: Circular or Fruchterman-Reingold
- Node color: By Louvain community (6 communities)
- Node size: By total_matches attribute
- Node labels: Always show (team names)
- Edge width: By weight (goals)
- Edge color: Light, curved edges

**match_communities_interpretation.png**: Annotated version
- Same as above but with annotations
- Label each community with interpretation (e.g., "Group A+B")
- Highlight interesting cross-community edges


### 3. Community Quality Metrics
Create custom visualizations in GEPHI:

**community_quality_heatmap.png**:
- Matrix showing modularity for each algorithm
- Color intensity = modularity value
- Can be created in matplotlib or as table in GEPHI