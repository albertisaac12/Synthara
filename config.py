import os
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Synthara Configuration
# ---------------------------------------------------------------------------

# Load variables from .env file (if present). This runs before anything else.
load_dotenv()

# Gemini API key — set in your .env file as: GEMINI_API_KEY=your-key-here
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

# The model to use for all agent LLM calls.
MODEL_NAME: str = "gemini-2.0-flash"

# Default path for the exported session graph.
SESSION_OUTPUT: str = "session.json"

# Maximum number of self-correction retries allowed per agent.
MAX_RETRIES: int = 1

# Confidence threshold below which Logician raises WEAK_EVIDENCE flag.
WEAK_EVIDENCE_THRESHOLD: float = 0.6

# Minimum citation count below which Logician raises CITATION_GAP flag.
MIN_CITATION_COUNT: int = 3

# Auditor score threshold below which AUDIT_FAIL is raised.
AUDIT_FAIL_THRESHOLD: float = 0.7
