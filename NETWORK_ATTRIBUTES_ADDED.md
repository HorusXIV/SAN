# Network Attributes Added for Gephi Visualization

This document summarizes the new attributes added to network files to facilitate Gephi visualizations.

## Date: 2025-12-27

## Files Modified

1. `src/network_generators/pass_networks.py`
2. `src/network_generators/match_networks.py`
3. `src/network_generators/unified_pass_network.py`

---

## Pass Networks (`pass_network_*.gexf`)

### New Node Attributes

#### Centrality Metrics
- **`degree`** - Simple degree count (number of connections)
- **`degree_centrality`** - Normalized degree centrality (0-1)
- **`betweenness_centrality`** - Betweenness centrality (0-1), calculated on undirected graph
- **`closeness_centrality`** - Closeness centrality (0-1), handles disconnected components
- **`pagerank`** - PageRank score, weighted by pass count

#### Network Structure
- **`kcore_number`** - K-core number for each node (useful for filtering to dense cores)

### Existing Community Detection Attributes (Already Present)
- `modularity_class_louvain` - Community ID from Louvain method
- `modularity_class_label_propagation` - Community ID from Label Propagation
- `modularity_class_greedy` - Community ID from Greedy Modularity
- `modularity_class_girvan_newman` - Community ID from Girvan-Newman (only for graphs < 500 nodes)

---

## Match Networks (`match_network_*.gexf`)

### New Node Attributes

#### Community Detection
- **`modularity_class_louvain`** - Community ID from Louvain method
- **`modularity_class_label_propagation`** - Community ID from Label Propagation
- **`modularity_class_greedy`** - Community ID from Greedy Modularity

These attributes enable coloring teams by detected communities in Gephi.

---

## Unified Pass Network (`pass_network_unified.gexf`)

### New Node Attributes

Same as individual pass networks:
- All centrality metrics (degree, degree_centrality, betweenness_centrality, closeness_centrality, pagerank)
- K-core numbers
- Community detection attributes (all 4 methods, though Girvan-Newman only for networks < 1000 nodes)

**Note**: For the unified network, community detection is performed on the largest connected component for efficiency.

---

## Gephi Usage Guide

### For Pass Networks (LE3 Visualizations)

**Node Sizing:**
- Size by `degree` or `betweenness_centrality`
- Appearance → Nodes → Ranking → Select attribute

**Node Coloring:**
- Color by `current_team_name` (team-based)
- Color by `betweenness_centrality` (gradient)
- Appearance → Nodes → Partition/Ranking

**Filtering:**
- Filter by `kcore_number` to show k-core subgraph
- Filter by `degree` to show high-degree nodes
- Filters → Attributes → Range

### For Community Detection (LE4 Visualizations)

**Node Coloring by Communities:**
- Appearance → Nodes → Partition
- Select: `modularity_class_louvain` (or other algorithm)
- Generate palette with distinct colors
- Apply

**Node Sizing:**
- Size by `degree` to emphasize important nodes
- Appearance → Nodes → Ranking → degree

**Comparing Algorithms:**
- Switch between `modularity_class_louvain`, `modularity_class_label_propagation`, etc.
- Use same layout for fair comparison

### For Match Networks (LE4 Visualizations)

**Node Coloring:**
- Color by `modularity_class_louvain` to show tournament structure
- Color by `goal_difference` (gradient) for performance

**Node Sizing:**
- Size by `total_matches` to show participation

---

## Regenerating Networks

To regenerate the networks with these new attributes:

```bash
# Pass networks (individual competitions)
python -m src.network_generators.pass_networks

# Match networks
python -m src.network_generators.match_networks

# Unified pass network (all competitions combined)
python -m src.network_generators.unified_pass_network
```

**Warning**: The unified pass network generation can take 10-30 minutes and requires significant memory, especially for betweenness centrality calculation.

---

## Implementation Details

### Centrality Calculations

- **Degree centrality**: Calculated on directed graph
- **Betweenness/Closeness**: Calculated on undirected version for consistency
- **Disconnected graphs**: Closeness centrality calculated per connected component
- **Weight consideration**: Edge weights (pass counts) are used where applicable

### Community Detection

- All algorithms run on **undirected** version of the network
- **Weight attribute**: Uses `weight` (pass count for passes, goals for matches)
- **Girvan-Newman**: Skipped for large graphs (>500 nodes for pass networks, >1000 for unified) due to computational cost

### Error Handling

- All metric calculations wrapped in try-except blocks
- Warnings logged if calculations fail
- Network generation continues even if some attributes fail

---

## Summary of What Changed

### Before
- Pass networks: Basic node attributes (name, team, position) + edge attributes (pass_count, accuracy)
- Match networks: Team stats + match results
- No centrality metrics, no k-core numbers
- Only pass networks had community detection

### After  
- Pass networks: **+ centrality metrics + k-core numbers** (community detection already present)
- Match networks: **+ community detection attributes**
- Unified pass network: **+ all centrality + k-core + community detection**
- All attributes ready for Gephi without additional computation

---

## Next Steps

1. Regenerate all network files on a machine with sufficient resources
2. Open networks in Gephi and verify all attributes are present in Data Laboratory
3. Create visualizations following the READMEs in `reports/figures/LE3/` and `reports/figures/LE4/`
4. No need to run Statistics→Modularity in Gephi - community attributes are pre-calculated
