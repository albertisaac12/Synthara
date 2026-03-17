from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from .Classtype import AgentName, NodeType, FlagType, NodeStatus

@dataclass
class GraphNode:
    id:               str
    agent:            AgentName
    node_type:        NodeType
    summary:          str
    confidence:       float
    inputs:           list[str]            = field(default_factory=list)
    triggered_by:     Optional[str]        = None
    output_artifact:  Optional[str]        = None
    flags:            list[FlagType]       = field(default_factory=list)
    timestamp:        str                  = field(default_factory=lambda: datetime.now().isoformat())
    status:           NodeStatus           = NodeStatus.ACTIVE