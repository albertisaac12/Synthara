import networkx as nx
import json
from typing import List, Optional, Dict
from datetime import datetime
from .graph_schema import GraphNode
from .Classtype import AgentName, NodeStatus, FlagType

class GraphManager:
    """
    Core service that manages the directed graph (DAG) of the Synthara project.
    Uses NetworkX DiGraph under the hood to track relationships between agent decisions.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.counters: Dict[str, int] = {agent.name: 0 for agent in AgentName}
        
        # Mapping AgentName to its 3-letter prefix
        self.prefixes = {
            AgentName.ARCHITECT: "ARC",
            AgentName.LIBRARIAN: "LIB",
            AgentName.LOGICIAN: "LOG",
            AgentName.DRAFTER: "DRA",
            AgentName.HUMANIZER: "HUM",
            AgentName.AUDITOR: "AUD"
        }

    def _generate_id(self, agent: AgentName) -> str:
        """Generates a collision-safe ID like ARC-001."""
        self.counters[agent.name] += 1
        prefix = self.prefixes.get(agent, "UNK")
        return f"{prefix}-{self.counters[agent.name]:03d}"

    def add_node(self, node: GraphNode) -> str:
        """
        Validates the node, adds it to the NetworkX graph, and establishes edges.
        Returns the assigned ID.
        """
        # Assign ID
        node_id = self._generate_id(node.agent)
        node.id = node_id
        
        # Add node with its full data as attributes
        # We store the object itself in a 'data' attribute for easy retrieval
        self.graph.add_node(node_id, data=node)

        # Create edges from inputs
        for input_id in node.inputs:
            if self.graph.has_node(input_id):
                self.graph.add_edge(input_id, node_id, type="input")

        # Create edge from triggered_by
        if node.triggered_by and self.graph.has_node(node.triggered_by):
            self.graph.add_edge(node.triggered_by, node_id, type="trigger")

        return node_id

    def get_ancestors(self, node_id: str, depth: int = 3) -> List[GraphNode]:
        """
        Walks backwards through the DAG from the given node up to depth hops.
        Returns nodes sorted from closest ancestor to furthest.
        """
        if not self.graph.has_node(node_id):
            return []

        ancestors = []
        visited = {node_id}
        
        # We use a simple breadth-first traversal on the reversed graph to track depth
        queue = [(node_id, 0)]
        
        while queue:
            current_id, current_depth = queue.pop(0)
            
            if current_depth >= depth:
                continue
                
            # Predecessors in a DiGraph are the 'parents'
            for pred in self.graph.predecessors(current_id):
                if pred not in visited:
                    visited.add(pred)
                    node_data = self.graph.nodes[pred]['data']
                    ancestors.append(node_data)
                    queue.append((pred, current_depth + 1))
        
        return ancestors

    def get_context_summary(self, node_id: str) -> str:
        """
        Formats ancestor context into a compact string.
        Must stay under ~300 tokens.
        """
        ancestors = self.get_ancestors(node_id, depth=3)
        if not ancestors:
            return "No prior context available."

        parts = []
        for node in ancestors:
            # Example: "LOG-003 flagged weak evidence because LIB-002 only returned 1 citation"
            flag_str = f" flagged {', '.join([f.value for f in node.flags])}" if node.flags else ""
            summary = node.summary[:100] + "..." if len(node.summary) > 100 else node.summary
            parts.append(f"{node.id}{flag_str} because {summary}")

        summary_str = ". ".join(parts)
        
        # Simple token count approximation (4 chars per token)
        if len(summary_str) > 1200:
            summary_str = summary_str[:1197] + "..."
            
        return summary_str

    def get_flagged_nodes(self) -> List[GraphNode]:
        """Returns all active nodes where flags is non-empty and status is not superseded."""
        flagged = []
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]['data']
            if node.flags and node.status != NodeStatus.SUPERSEDED:
                flagged.append(node)
        return flagged

    def supersede(self, old_node_id: str, new_node_id: str) -> None:
        """
        Marks the old node's status as superseded and links it to the new node.
        """
        if self.graph.has_node(old_node_id) and self.graph.has_node(new_node_id):
            old_node = self.graph.nodes[old_node_id]['data']
            old_node.status = NodeStatus.SUPERSEDED
            
            # Create a special edge to track the supersession path
            self.graph.add_edge(old_node_id, new_node_id, type="superseded_by")

    def export_session(self, filepath: str) -> None:
        """Serializes the entire graph to a JSON file."""
        data = {
            "nodes": [],
            "edges": []
        }
        
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]['data']
            # Convert GraphNode to dict for JSON serialization
            node_dict = {
                "id": node.id,
                "agent": node.agent.value,
                "node_type": node.node_type.value,
                "summary": node.summary,
                "confidence": node.confidence,
                "inputs": node.inputs,
                "triggered_by": node.triggered_by,
                "output_artifact": node.output_artifact,
                "flags": [f.value for f in node.flags],
                "timestamp": node.timestamp,
                "status": node.status.value
            }
            data["nodes"].append(node_dict)
            
        for u, v, attrs in self.graph.edges(data=True):
            data["edges"].append({
                "from": u,
                "to": v,
                "type": attrs.get("type", "unknown")
            })
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
