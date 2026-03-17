import sys
import os

# Add the project root to sys.path so we can import 'Core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.graph_manager import GraphManager
from Core.graph_schema import GraphNode
from Core.Classtype import AgentName, NodeType, FlagType, NodeStatus

def test_graph_manager():
    gm = GraphManager()
    
    # 1. Test add_node
    print("--- Testing add_node ---")
    node1 = GraphNode(
        id="", # Will be assigned
        agent=AgentName.ARCHITECT,
        node_type=NodeType.DECISION,
        summary="Defined the claim as exploratory",
        confidence=0.9,
        inputs=[]
    )
    id1 = gm.add_node(node1)
    print(f"Added node 1: {id1}")

    node2 = GraphNode(
        id="",
        agent=AgentName.LIBRARIAN,
        node_type=NodeType.DECISION,
        summary="Returned 1 citation for the claim",
        confidence=0.7,
        inputs=[id1]
    )
    id2 = gm.add_node(node2)
    print(f"Added node 2: {id2}")

    node3 = GraphNode(
        id="",
        agent=AgentName.LOGICIAN,
        node_type=NodeType.FLAG,
        summary="Flagged weak evidence",
        confidence=0.4,
        inputs=[id2],
        flags=[FlagType.WEAK_EVIDENCE]
    )
    id3 = gm.add_node(node3)
    print(f"Added node 3: {id3}")

    # 2. Test get_ancestors
    print("\n--- Testing get_ancestors ---")
    ancestors = gm.get_ancestors(id3, depth=3)
    print(f"Ancestors of {id3}: {[n.id for n in ancestors]}")

    # 3. Test get_context_summary
    print("\n--- Testing get_context_summary ---")
    summary = gm.get_context_summary(id3)
    print(f"Context Summary: {summary}")

    # 4. Test get_flagged_nodes
    print("\n--- Testing get_flagged_nodes ---")
    flagged = gm.get_flagged_nodes()
    print(f"Flagged nodes: {[n.id for n in flagged]}")

    # 5. Test supersede
    print("\n--- Testing supersede ---")
    node4 = GraphNode(
        id="",
        agent=AgentName.LOGICIAN,
        node_type=NodeType.CORRECTION,
        summary="Corrected analysis after better citations",
        confidence=0.9,
        inputs=[id2]
    )
    id4 = gm.add_node(node4)
    print(f"Added node 4: {id4}")
    gm.supersede(id3, id4)
    print(f"Node {id3} status: {gm.graph.nodes[id3]['data'].status}")
    
    # Verify it doesn't show up in flagged nodes anymore (if flagged)
    flagged_after = gm.get_flagged_nodes()
    print(f"Flagged nodes after supersede: {[n.id for n in flagged_after]}")

    # 6. Test export_session
    print("\n--- Testing export_session ---")
    export_path = os.path.abspath("test_session.json")
    gm.export_session(export_path)
    print(f"Session exported to {export_path}")
    
    if os.path.exists(export_path):
        print("Export file exists.")

if __name__ == "__main__":
    test_graph_manager()
