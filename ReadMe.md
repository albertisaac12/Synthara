# Synthara

**Synthara** is a multi-agent AI research pipeline that takes a raw research claim, routes it through six specialized AI agents, records every decision in an auditable directed graph (DAG), and produces a polished, fact-checked research paragraph along with a fully exportable session.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [The Agent Team](#the-agent-team)
- [The Graph Engine](#the-graph-engine)
- [Node Types & Flags](#node-types--flags)
- [Self-Correction Loops](#self-correction-loops)
- [Project Structure](#project-structure)
- [Setup & Configuration](#setup--configuration)
- [Running Synthara](#running-synthara)
- [Session Output](#session-output)
- [Example Run](#example-run)

---

## How It Works

You give Synthara a claim like:

> *"Climate change is primarily driven by human industrial activity."*

Synthara then runs it through a sequential pipeline of six agents. Each agent reads its predecessor's output, consults the rolling graph context (last 3 hops of ancestor summaries), calls the Gemini LLM, and writes its result into a shared DAG as a `GraphNode`. At the end, a polished research paragraph is returned alongside a complete JSON session log.

---

## Architecture

```
User Claim
    │
    ▼
┌─────────────┐
│  Architect  │  Classifies claim type, refines wording, identifies sub-questions
└──────┬──────┘
       │ (input edge)
       ▼
┌─────────────┐
│  Librarian  │  Retrieves 4 relevant academic citations (LLM-simulated)
└──────┬──────┘
       │ (input edge)
       ▼
┌─────────────┐
│  Logician   │  Evaluates evidence strength; raises WEAK_EVIDENCE / CITATION_GAP flags
└──────┬──────┘
       │      ↩ (if flagged → supersede Librarian, retry)
       ▼
┌─────────────┐
│   Drafter   │  Writes 150–200 word academic paragraph citing sources
└──────┬──────┘
       │ (input edge)
       ▼
┌─────────────┐
│  Humanizer  │  Strips AI-isms, natural academic tone, preserves citations
└──────┬──────┘
       │ (input edge)
       ▼
┌─────────────┐
│   Auditor   │  Scores on 4 criteria (0.0–1.0); raises AUDIT_FAIL if < 0.7
└──────┬──────┘
       │      ↩ (if FAIL → supersede Drafter+Humanizer, retry)
       ▼
Session Export (session.json)
Final Output
```

---

## The Agent Team

| Agent | Node Prefix | Role |
|---|---|---|
| **Architect** | `ARC` | Parses the claim and produces a structured JSON breakdown (claim type, refined claim, sub-questions) |
| **Librarian** | `LIB` | Generates 4 plausible academic citations with author, year, journal, and relevance notes |
| **Logician**  | `LOG` | Rates evidence strength, counts citations, identifies logical gaps; auto-raises quality flags |
| **Drafter**   | `DRA` | Writes a 150–200 word research paragraph inline-citing the retrieved sources |
| **Humanizer** | `HUM` | Rewrites for natural tone, removes AI-isms while preserving all facts and citations |
| **Auditor**   | `AUD` | Final quality gate — scores output 0.0–1.0 across factual accuracy, logic, completeness, and citation use |

---

## The Graph Engine

Every agent action produces a **`GraphNode`** stored in a NetworkX `DiGraph` managed by `GraphManager`.

### GraphNode Fields

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Auto-assigned collision-safe ID, e.g. `LOG-002` |
| `agent` | `AgentName` | Which agent produced this node |
| `node_type` | `NodeType` | Classification of what the node represents |
| `summary` | `str` | One-sentence description of the agent's action |
| `confidence` | `float` | Agent's self-assessed confidence (0.0–1.0) |
| `inputs` | `list[str]` | Node IDs this node is derived from |
| `triggered_by` | `str` | Optional — node ID that triggered this correction |
| `output_artifact` | `str` | The actual output (paragraph, JSON citations, etc.) |
| `flags` | `list[FlagType]` | Quality issues raised by the agent |
| `timestamp` | `str` | ISO timestamp |
| `status` | `NodeStatus` | `active` or `superseded` |

### Graph Edges

| Edge Type | Meaning |
|---|---|
| `input` | Node B used Node A's output as input |
| `trigger` | Node A triggered Node B to run |
| `superseded_by` | Node A was replaced by the corrected Node B |

### Context Window (Ancestor Lookup)

Before each agent runs, the orchestrator calls `GraphManager.get_context_summary(node_id)` — this walks up to **3 hops** of ancestors in the DAG and formats them into a compact string (capped at ~300 tokens), which is passed to the agent's LLM prompt. This gives each agent awareness of everything that came before it without blowing the context limit.

---

## Node Types & Flags

### NodeType

| Value | Meaning |
|---|---|
| `decision` | The agent made an analytical decision |
| `output` | The agent produced content (citations, paragraph, etc.) |
| `flag` | The agent detected a quality issue |
| `correction` | The agent produced a corrected version of a prior output |
| `superseded` | This node has been replaced (kept for auditability) |

### FlagType

| Flag | Raised By | Trigger |
|---|---|---|
| `weak_evidence` | Logician | Confidence < 0.6 |
| `citation_gap` | Logician | Citation count < 3 |
| `unsupported_claim` | Logician | Claim not backed by any citation |
| `style_break` | Humanizer | Detects non-human writing patterns |
| `audit_fail` | Auditor | Overall score < 0.7 |

---

## Self-Correction Loops

Synthara has two built-in correction loops (each runs at most `MAX_RETRIES` times, default: 1):

**Loop 1 — Evidence Quality (after Logician)**
- Triggered when Logician raises `weak_evidence` or `citation_gap`
- Supersedes the old Librarian node → re-runs Librarian with a retry prompt that lists the specific gaps
- Re-runs Logician on the new citations
- The old nodes remain in the graph with `status = superseded` for full auditability

**Loop 2 — Output Quality (after Auditor)**
- Triggered when Auditor score < `AUDIT_FAIL_THRESHOLD` (default: 0.7)
- Supersedes old Drafter + Humanizer nodes → passes Auditor's recommendation to the Drafter
- Re-runs both Drafter and Humanizer
- Re-runs Auditor on the revised paragraph

---

## Project Structure

```
Project2/
├── Core/
│   ├── Classtype/
│   │   ├── agentname.py      # AgentName enum
│   │   ├── flagtype.py       # FlagType enum
│   │   ├── nodestatus.py     # NodeStatus enum
│   │   ├── nodetype.py       # NodeType enum
│   │   └── __init__.py
│   ├── graph_manager.py      # DAG service (NetworkX)
│   ├── graph_schema.py       # GraphNode dataclass
│   └── __init__.py
├── LLM/
│   ├── llm_client.py         # Gemini API wrapper
│   └── __init__.py
├── Agents/
│   ├── base_agent.py         # Abstract base class
│   ├── architect.py
│   ├── librarian.py
│   ├── logician.py
│   ├── drafter.py
│   ├── humanizer.py
│   ├── auditor.py
│   └── __init__.py
├── orchestrator.py           # Full pipeline coordinator
├── config.py                 # Thresholds and settings (loads from .env)
├── main.py                   # CLI entry point
├── .env                      # Your API key — gitignored, never committed
├── .env.example              # Template showing required variables
├── requirments.txt
└── README.md
```

---

## Setup & Configuration

### 1. Clone and activate the virtual environment

```powershell
cd Project2
.\venv\Scripts\Activate
```

### 2. Install dependencies

```powershell
pip install -r requirments.txt
```

### 3. Set your Gemini API key

Copy the example env file and fill in your key:

```powershell
copy .env.example .env
```

Then open `.env` and replace the placeholder:

```
GEMINI_API_KEY=your-api-key-here
```

The `.env` file is gitignored — your key will never be committed. The `.env.example` template is committed so collaborators know which variables are needed.

> Get a free API key at [Google AI Studio](https://aistudio.google.com/app/apikey).


### 4. Tune thresholds (optional)

All tunable parameters live in `config.py`:

```python
MODEL_NAME              = "gemini-2.0-flash"   # LLM model
SESSION_OUTPUT          = "session.json"        # Output path
MAX_RETRIES             = 1                     # Correction loop limit
WEAK_EVIDENCE_THRESHOLD = 0.6                   # Logician flag trigger
MIN_CITATION_COUNT      = 3                     # Logician flag trigger
AUDIT_FAIL_THRESHOLD    = 0.7                   # Auditor fail trigger
```

---

## Running Synthara

```powershell
# Option 1 — positional argument
python main.py "Climate change is primarily driven by human industrial activity"

# Option 2 — named flag
python main.py --claim "Quantum computing will obsolete RSA encryption by 2035"

# Option 3 — interactive prompt
python main.py
# → Enter a research claim: _
```

---

## Session Output

After every run, Synthara writes a `session.json` file containing the full graph:

```json
{
  "nodes": [
    {
      "id": "ARC-001",
      "agent": "Architect",
      "node_type": "decision",
      "summary": "Claim classified as factual with 3 sub-questions identified",
      "confidence": 0.88,
      "inputs": [],
      "flags": [],
      "status": "active",
      "output_artifact": "{ ... structured claim JSON ... }"
    },
    ...
  ],
  "edges": [
    { "from": "ARC-001", "to": "LIB-001", "type": "input" },
    { "from": "LOG-001", "to": "LOG-002", "type": "superseded_by" },
    ...
  ]
}
```

This file is a complete, auditable record of how the output was produced — every decision, every flag, every correction — useful for debugging, auditing, or replaying sessions.

---

## Example Run

```
============================================================
  SYNTHARA PIPELINE  |  Claim: Climate change is primarily...
============================================================

[1/6] Architect — structuring the claim...
  [ARCHITECT   ] ARC-001  —  Claim classified as factual, 3 sub-questions identified

[2/6] Librarian — retrieving citations...
  [LIBRARIAN   ] LIB-001  —  Retrieved 4 citations on industrial emissions and climate

[3/6] Logician — evaluating evidence...
  [LOGICIAN    ] LOG-001  —  Evidence rated strong, no gaps detected

[4/6] Drafter — writing research paragraph...
  [DRAFTER     ] DRA-001  —  150-word paragraph written citing 3 sources

[5/6] Humanizer — polishing the paragraph...
  [HUMANIZER   ] HUM-001  —  Removed 2 AI-isms, tone naturalised

[6/6] Auditor — running quality audit...
  [AUDITOR     ] AUD-001  —  Score 0.91, PASS

============================================================
  PIPELINE COMPLETE
============================================================

────────────────────────────────────────────────────────────
  FINAL OUTPUT
────────────────────────────────────────────────────────────
Human industrial activity has been identified as the dominant
driver of contemporary climate change, a conclusion supported
by decades of atmospheric and geophysical research...
────────────────────────────────────────────────────────────
  Audit Score   : 0.91  |  Verdict: PASS
  Total Nodes   : 6
  Flagged Nodes : None
  Session saved : session.json
────────────────────────────────────────────────────────────
```