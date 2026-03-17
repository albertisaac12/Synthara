from enum import Enum
class NodeType(Enum):
    DECISION  = "decision"
    OUTPUT    = "output"
    FLAG      = "flag"
    CORRECTION = "correction"
    SUPERSEDED = "superseded"