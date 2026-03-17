import json
from Agents.base_agent import BaseAgent
from Core.graph_schema import GraphNode
from Core.Classtype import AgentName, NodeType, FlagType
from config import AUDIT_FAIL_THRESHOLD


PROMPT_TEMPLATE = """\
You are the Auditor agent — the final quality gate in the Synthara research pipeline.
You must rigorously evaluate the polished output and decide if it passes.

Original claim:
{claim}

Final paragraph from Humanizer:
{paragraph}

Citations used in the pipeline:
{citations}

Full pipeline context:
{graph_context}

Evaluate on these criteria:
1. Factual accuracy — do claims align with the citations?
2. Logical consistency — does the argument flow without contradictions?
3. Completeness — does it address the original claim fully?
4. Citation usage — are citations used correctly?

Respond in this exact JSON format (no markdown, no extra text):
{{
  "score": <float 0.0–1.0>,
  "verdict": "<PASS | FAIL>",
  "issues": ["<issue 1>", "<issue 2>"],
  "recommendation": "<What should be fixed if FAIL, or empty string if PASS>",
  "confidence": <float 0.0–1.0>,
  "summary": "<One sentence audit verdict>"
}}
"""


class AuditorAgent(BaseAgent):
    """
    Final quality gate. Scores the output and raises AUDIT_FAIL if below threshold.
    """

    def run(self, context: str, graph_context: str = "",
            claim: str = "", citations: str = "") -> str:
        prompt = PROMPT_TEMPLATE.format(
            claim=claim or context,
            paragraph=context,
            citations=citations or "Not provided",
            graph_context=graph_context or "None"
        )
        raw = self.llm.generate(prompt)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {
                "score":          0.5,
                "verdict":        "FAIL",
                "issues":         [raw[:200]],
                "recommendation": "Review the paragraph manually.",
                "confidence":     0.5,
                "summary":        "Audit inconclusive due to parse error."
            }

        score = float(data.get("score", 0.5))
        flags = [FlagType.AUDIT_FAIL] if score < AUDIT_FAIL_THRESHOLD else []
        node_type = NodeType.FLAG if flags else NodeType.OUTPUT

        node = GraphNode(
            id="",
            agent=AgentName.AUDITOR,
            node_type=node_type,
            summary=data.get("summary", "Audit complete."),
            confidence=float(data.get("confidence", 0.5)),
            flags=flags,
            output_artifact=json.dumps({
                "score":          score,
                "verdict":        data.get("verdict", "FAIL"),
                "issues":         data.get("issues", []),
                "recommendation": data.get("recommendation", "")
            }, indent=2)
        )
        node_id = self._add_to_graph(node)

        # Store score on instance so the orchestrator can read it
        self.last_score  = score
        self.last_verdict = data.get("verdict", "FAIL")
        self.last_recommendation = data.get("recommendation", "")

        return node_id
