from enum import Enum
class FlagType(Enum):
    WEAK_EVIDENCE     = "weak_evidence"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    CITATION_GAP      = "citation_gap"
    STYLE_BREAK       = "style_break"
    AUDIT_FAIL        = "audit_fail"