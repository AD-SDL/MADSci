"""Transfer Manager - Graph Logic"""
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import heapq

class TransferGraph:
    """Graph for finding transfer paths."""
    
    def __init__(self):
        # Graph: location -> [(target_location, robot_name, cost), ...]
        self.edges: Dict[str, List[Tuple[str, str, float]]] = defaultdict(list)
        self.locations: Set[str] = set()
    
    def add_location(self, location: str):
        """Add a location to the graph."""
        self.locations.add(location)
    
    def add_edge(self, source: str, target: str, robot: str, cost: float = 1.0):
        """Add a transfer edge between two locations."""
        if not robot or not robot.strip():
            print(f"ERROR: Cannot add edge with empty robot: {source} -> {target}")
            return
            
        self.edges[source].append((target, robot, cost))
        self.locations.add(source)
        self.locations.add(target)
        print(f"Added edge: {source} -> {target} via {robot} (cost: {cost})")
    
    def find_shortest_path(self, source: str, target: str) -> Optional[List[Dict]]:
        """Find shortest path using Dijkstra's algorithm."""
        print(f"Finding path from '{source}' to '{target}'")
        
        if source not in self.locations:
            print(f"Source '{source}' not in graph locations: {sorted(self.locations)}")
            return None
        if target not in self.locations:
            print(f"Target '{target}' not in graph locations: {sorted(self.locations)}")
            return None
        
        print(f"Source edges: {self.edges.get(source, [])}")
        
        # Dijkstra's algorithm
        distances = {loc: float('inf') for loc in self.locations}
        distances[source] = 0
        previous = {}
        robots_used = {}
        
        pq = [(0, source)]
        visited = set()
        
        while pq:
            current_dist, current = heapq.heappop(pq)
            
            if current in visited:
                continue
            
            visited.add(current)
            print(f"Visiting: {current} (distance: {current_dist})")
            
            if current == target:
                print(f"Found target! Reconstructing path...")
                # Reconstruct path
                path = []
                node = target
                
                while node in previous:
                    prev_node = previous[node]
                    robot = robots_used[node]
                    print(f"Path step: {prev_node} -> {node} via '{robot}'")
                    path.append({
                        "source": prev_node,
                        "target": node,
                        "robot": robot
                    })
                    node = prev_node
                
                path.reverse()
                print(f"Complete path: {path}")
                return path
            
            # Check neighbors
            for neighbor, robot, edge_cost in self.edges[current]:
                print(f"Checking edge: {current} -> {neighbor} via '{robot}' (cost: {edge_cost})")
                distance = current_dist + edge_cost
                
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current
                    robots_used[neighbor] = robot
                    heapq.heappush(pq, (distance, neighbor))
                    print(f"Updated distance to {neighbor}: {distance}")
        
        print(f"No path found from '{source}' to '{target}'")
        return None
