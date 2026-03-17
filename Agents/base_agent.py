from abc import ABC, abstractmethod
from Core.graph_manager import GraphManager
from Core.graph_schema import GraphNode
from LLM.llm_client import LLMClient


class BaseAgent(ABC):
    """
    Abstract base class for all Synthara agents.
    Every agent receives a shared GraphManager and LLMClient,
    and must implement the `run` method.
    """

    def __init__(self, graph_manager: GraphManager, llm_client: LLMClient):
        self.gm = graph_manager
        self.llm = llm_client

    @abstractmethod
    def run(self, context: str, graph_context: str = "") -> str:
        """
        Execute the agent's task.

        Args:
            context:       Primary input for this agent (e.g., the claim, prior output).
            graph_context: Compact ancestor summary from GraphManager.get_context_summary().

        Returns:
            The assigned node ID after registering the result in the graph.
        """
        ...

    def _add_to_graph(self, node: GraphNode) -> str:
        """Registers the node in the graph and returns its assigned ID."""
        return self.gm.add_node(node)
