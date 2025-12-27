# LE4 Figures - Community Detection Visualizations

This directory should contain the following community detection visualizations generated in GEPHI:

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
- Highlight differences in community assignments

**pass_community_largest.png**: Zoom into largest communities
- Extract 3 largest communities as separate layouts
- Show internal structure and key players
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

### 3. Community Size Distributions (from notebook)
Already generated in notebook - save matplotlib outputs:
- `community_size_distributions.png`
- `algorithm_comparison_metrics.png`

### 4. Community Quality Metrics
Create custom visualizations in GEPHI:

**community_quality_heatmap.png**:
- Matrix showing modularity for each algorithm
- Color intensity = modularity value
- Can be created in matplotlib or as table in GEPHI

## GEPHI Workflow for Community Detection

### Step 1: Import Network
1. File → Open → Select .gexf file
2. Verify community attributes are loaded (check Data Laboratory)

### Step 2: Apply Layout
1. Layout → ForceAtlas 2
2. Settings:
   - Scaling: 10.0
   - Gravity: 1.0
   - Prevent Overlap: checked
3. Run until stable (30-60 seconds)

### Step 3: Apply Community Colors
1. Appearance → Nodes → Partition
2. Select attribute: "modularity_class" or "community"
3. Palette: Generate → Custom palette with distinct colors
4. Apply

### Step 4: Size Nodes
1. Appearance → Nodes → Ranking
2. Select attribute: "degree"
3. Min size: 5, Max size: 50
4. Apply

### Step 5: Configure Edges
1. Appearance → Edges → Unique
2. Color: Gray (#CCCCCC)
3. Edge Weight → Ranking
4. Min: 0.5, Max: 5.0

### Step 6: Labels
1. Show Labels: Click "T" icon
2. Appearance → Labels → Size
3. Proportional to node size
4. Size range: 8-18
5. Color: Black with white halo

### Step 7: Preview and Export
1. Preview → Settings:
   - Show labels
   - Node borders: off
   - Background: white
   - Anti-aliasing: on
2. Refresh
3. Export: PNG, 2000x1500, 300 DPI

## Community Detection in GEPHI

If you want to run community detection directly in GEPHI:

1. Statistics → Modularity
2. Algorithm: Louvain
3. Resolution: 1.0
4. Randomize: unchecked (for reproducibility)
5. Use weights: checked
6. Run → Creates "Modularity Class" attribute

Then follow coloring steps above.

## Notes

- **Community Stability**: For Label Propagation, run multiple times and choose best
- **Color Consistency**: Use same colors for same communities across figures
- **Node Labels**: Only show for high-degree nodes to avoid clutter in large networks
- **Edge Filtering**: Consider showing only edges with weight ≥ 5 for cleaner visualization

## Figure References for LaTeX

```latex
\begin{figure}[h]
\centering
\includegraphics[width=0.8\textwidth]{figures/LE4/pass_communities_louvain.png}
\caption{Pass network communities detected using Louvain method. Colors represent 11 distinct communities corresponding to Bundesliga teams.}
\label{fig:pass_communities_louvain}
\end{figure}
```
