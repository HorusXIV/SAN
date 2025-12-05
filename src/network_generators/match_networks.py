"""
Match Network Generator
Creates directed networks where nodes represent teams and edges represent matches.
"""

import networkx as nx
from pathlib import Path
from collections import defaultdict

from src.common import load_json_fixed, setup_logger
from src.config import (
    DATA_DIR,
    LOG_DIR,
    MATCHES_DIR,
    MATCH_NETWORKS_DIR,
    TEAMS_FILE
)

logger = setup_logger(__name__, log_dir=LOG_DIR, file_prefix='match_network')


def load_teams_info(teams_file):
    """Load team information from teams.json"""
    teams_data = load_json_fixed(teams_file)
    
    teams_info = {}
    for team in teams_data:
        team_id = str(team['wyId'])
        teams_info[team_id] = {
            'name': team['name'],
            'area': team.get('area', {}).get('name', 'Unknown'),
            'official_name': team.get('officialName', team['name'])
        }
    return teams_info


def create_match_network(matches_file, teams_info, competition_name):
    """Create a directed network from match data."""
    matches = load_json_fixed(matches_file)
    
    G = nx.DiGraph()
    G.graph['competition'] = competition_name
    G.graph['total_matches'] = len(matches)
    
    team_stats = defaultdict(lambda: {
        'total_matches': 0,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'goals_scored': 0,
        'goals_conceded': 0
    })
    
    edges = defaultdict(lambda: {
        'total_goals': 0,
        'matches': 0,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'dates': [],
        'venues': []
    })
    
    for match in matches:
        if match['status'] != 'Played':
            continue
        
        teams_data = match['teamsData']
        if len(teams_data) != 2:
            continue
        
        team_ids = list(teams_data.keys())
        team1_id = team_ids[0]
        team2_id = team_ids[1]
        
        team1_data = teams_data[team1_id]
        team2_data = teams_data[team2_id]
        
        score1 = team1_data['score']
        score2 = team2_data['score']
        
        date = match.get('date', 'Unknown')
        venue = match.get('venue', 'Unknown')
        winner = match.get('winner', 0)
        
        for tid in [team1_id, team2_id]:
            if tid not in G:
                G.add_node(tid)
        
        for tid, score, opp_score in [(team1_id, score1, score2), (team2_id, score2, score1)]:
            team_stats[tid]['total_matches'] += 1
            team_stats[tid]['goals_scored'] += score
            team_stats[tid]['goals_conceded'] += opp_score
            
            if score > opp_score:
                team_stats[tid]['wins'] += 1
            elif score < opp_score:
                team_stats[tid]['losses'] += 1
            else:
                team_stats[tid]['draws'] += 1
        
        edge_key = (team1_id, team2_id)
        edges[edge_key]['total_goals'] += score1
        edges[edge_key]['matches'] += 1
        edges[edge_key]['dates'].append(date)
        edges[edge_key]['venues'].append(venue)
        
        if winner == int(team1_id):
            edges[edge_key]['wins'] += 1
        elif winner == int(team2_id):
            edges[edge_key]['losses'] += 1
        else:
            edges[edge_key]['draws'] += 1
        
        edge_key_reverse = (team2_id, team1_id)
        edges[edge_key_reverse]['total_goals'] += score2
        edges[edge_key_reverse]['matches'] += 1
        edges[edge_key_reverse]['dates'].append(date)
        edges[edge_key_reverse]['venues'].append(venue)
        
        if winner == int(team2_id):
            edges[edge_key_reverse]['wins'] += 1
        elif winner == int(team1_id):
            edges[edge_key_reverse]['losses'] += 1
        else:
            edges[edge_key_reverse]['draws'] += 1
    
    for team_id in G.nodes():
        stats = team_stats[team_id]
        team_info = teams_info.get(team_id, {})
        
        G.nodes[team_id]['team_id'] = team_id
        G.nodes[team_id]['team_name'] = team_info.get('name', f'Team {team_id}')
        G.nodes[team_id]['area'] = team_info.get('area', 'Unknown')
        G.nodes[team_id]['official_name'] = team_info.get('official_name', team_info.get('name', f'Team {team_id}'))
        G.nodes[team_id]['total_matches'] = stats['total_matches']
        G.nodes[team_id]['wins'] = stats['wins']
        G.nodes[team_id]['losses'] = stats['losses']
        G.nodes[team_id]['draws'] = stats['draws']
        G.nodes[team_id]['goals_scored'] = stats['goals_scored']
        G.nodes[team_id]['goals_conceded'] = stats['goals_conceded']
        G.nodes[team_id]['goal_difference'] = stats['goals_scored'] - stats['goals_conceded']
    
    for (team1_id, team2_id), edge_data in edges.items():
        if edge_data['matches'] > 0:
            G.add_edge(
                team1_id, 
                team2_id,
                weight=edge_data['total_goals'],
                matches=edge_data['matches'],
                weight_normalized=edge_data['total_goals'] / edge_data['matches'],
                wins=edge_data['wins'],
                losses=edge_data['losses'],
                draws=edge_data['draws'],
                dates='; '.join(edge_data['dates'][:5]),
                venues='; '.join(set(edge_data['venues'][:5]))
            )
    
    return G


def create_unified_network(match_files, teams_info, exclude_competitions=None):
    """Create a unified network from multiple match files."""
    if exclude_competitions is None:
        exclude_competitions = []
    
    G = nx.DiGraph()
    G.graph['type'] = 'unified'
    G.graph['competitions'] = []
    
    team_stats = defaultdict(lambda: {
        'total_matches': 0,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'goals_scored': 0,
        'goals_conceded': 0
    })
    
    edges = defaultdict(lambda: {
        'total_goals': 0,
        'matches': 0,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'competitions': set()
    })
    
    total_matches = 0
    
    for match_file in match_files:
        competition_name = match_file.stem.replace('matches_', '')
        
        if competition_name in exclude_competitions:
            continue
        
        logger.debug(f"Processing {competition_name}")
        G.graph['competitions'].append(competition_name)
        
        matches = load_json_fixed(match_file)
        
        for match in matches:
            if match['status'] != 'Played':
                continue
            
            teams_data = match['teamsData']
            if len(teams_data) != 2:
                continue
            
            total_matches += 1
            
            team_ids = list(teams_data.keys())
            team1_id = team_ids[0]
            team2_id = team_ids[1]
            
            team1_data = teams_data[team1_id]
            team2_data = teams_data[team2_id]
            
            score1 = team1_data['score']
            score2 = team2_data['score']
            winner = match.get('winner', 0)
            
            for tid in [team1_id, team2_id]:
                if tid not in G:
                    G.add_node(tid)
            
            for tid, score, opp_score in [(team1_id, score1, score2), (team2_id, score2, score1)]:
                team_stats[tid]['total_matches'] += 1
                team_stats[tid]['goals_scored'] += score
                team_stats[tid]['goals_conceded'] += opp_score
                
                if score > opp_score:
                    team_stats[tid]['wins'] += 1
                elif score < opp_score:
                    team_stats[tid]['losses'] += 1
                else:
                    team_stats[tid]['draws'] += 1
            
            edge_key = (team1_id, team2_id)
            edges[edge_key]['total_goals'] += score1
            edges[edge_key]['matches'] += 1
            edges[edge_key]['competitions'].add(competition_name)
            
            if winner == int(team1_id):
                edges[edge_key]['wins'] += 1
            elif winner == int(team2_id):
                edges[edge_key]['losses'] += 1
            else:
                edges[edge_key]['draws'] += 1
            
            edge_key_reverse = (team2_id, team1_id)
            edges[edge_key_reverse]['total_goals'] += score2
            edges[edge_key_reverse]['matches'] += 1
            edges[edge_key_reverse]['competitions'].add(competition_name)
            
            if winner == int(team2_id):
                edges[edge_key_reverse]['wins'] += 1
            elif winner == int(team1_id):
                edges[edge_key_reverse]['losses'] += 1
            else:
                edges[edge_key_reverse]['draws'] += 1
    
    G.graph['total_matches'] = total_matches
    
    for team_id in G.nodes():
        stats = team_stats[team_id]
        team_info = teams_info.get(team_id, {})
        
        G.nodes[team_id]['team_id'] = team_id
        G.nodes[team_id]['team_name'] = team_info.get('name', f'Team {team_id}')
        G.nodes[team_id]['area'] = team_info.get('area', 'Unknown')
        G.nodes[team_id]['official_name'] = team_info.get('official_name', team_info.get('name', f'Team {team_id}'))
        G.nodes[team_id]['total_matches'] = stats['total_matches']
        G.nodes[team_id]['wins'] = stats['wins']
        G.nodes[team_id]['losses'] = stats['losses']
        G.nodes[team_id]['draws'] = stats['draws']
        G.nodes[team_id]['goals_scored'] = stats['goals_scored']
        G.nodes[team_id]['goals_conceded'] = stats['goals_conceded']
        G.nodes[team_id]['goal_difference'] = stats['goals_scored'] - stats['goals_conceded']
    
    for (team1_id, team2_id), edge_data in edges.items():
        if edge_data['matches'] > 0:
            G.add_edge(
                team1_id, 
                team2_id,
                weight=edge_data['total_goals'],
                matches=edge_data['matches'],
                weight_normalized=edge_data['total_goals'] / edge_data['matches'],
                wins=edge_data['wins'],
                losses=edge_data['losses'],
                draws=edge_data['draws'],
                competitions='; '.join(sorted(edge_data['competitions']))
            )
    
    return G


def main():
    """Generate all match-based networks"""
    logger.info("Starting match network generation")
    
    MATCH_NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("Loading team information")
    teams_info = load_teams_info(TEAMS_FILE)
    
    competitions = ['England', 'France', 'Germany', 'Italy', 'Spain', 'European_Championship', 'World_Cup']
    
    logger.info(f"Generating individual networks for {len(competitions)} competitions")
    
    for competition in competitions:
        matches_file = MATCHES_DIR / f'matches_{competition}.json'
        if not matches_file.exists():
            logger.warning(f"{matches_file} not found, skipping")
            continue
        
        logger.debug(f"Processing {competition}")
        G = create_match_network(matches_file, teams_info, competition)
        
        output_file = MATCH_NETWORKS_DIR / f'match_network_{competition}.gexf'
        nx.write_gexf(G, output_file)
    
    logger.info("Generating unified network (excluding World Cup)")
    
    match_files = [MATCHES_DIR / f'matches_{comp}.json' for comp in competitions]
    match_files = [f for f in match_files if f.exists()]
    
    G_unified = create_unified_network(match_files, teams_info, exclude_competitions=['World_Cup'])
    
    output_file = MATCH_NETWORKS_DIR / 'match_network_unified.gexf'
    nx.write_gexf(G_unified, output_file)
    
    logger.info(f"Complete: {G_unified.number_of_nodes()} nodes, {G_unified.number_of_edges()} edges")


if __name__ == '__main__':
    main()
