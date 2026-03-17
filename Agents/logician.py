import json
from Agents.base_agent import BaseAgent
from Core.graph_schema import GraphNode
from Core.Classtype import AgentName, NodeType, FlagType
from config import WEAK_EVIDENCE_THRESHOLD, MIN_CITATION_COUNT


PROMPT_TEMPLATE = """\
You are the Logician agent in a multi-agent research pipeline called Synthara.
Your job is to evaluate the quality of evidence and spot logical weaknesses.

Claim context:
{context}

Citations provided by Librarian:
{citations}

Prior pipeline context:
{graph_context}

Evaluate the evidence rigorously. Respond in this exact JSON format (no markdown, no extra text):
{{
  "evidence_strength": "<strong | moderate | weak>",
  "logical_gaps": ["<gap 1>", "<gap 2>"],
  "citation_count": <integer — number of valid citations>,
  "confidence": <float 0.0–1.0 reflecting how well the evidence supports the claim>,
  "summary": "<One sentence evaluation summary>"
}}
"""


class LogicianAgent(BaseAgent):
    """
    Evaluates logical coherence and evidence quality.
    Raises FlagType.WEAK_EVIDENCE or FlagType.CITATION_GAP when thresholds are breached.
    """

    def run(self, context: str, graph_context: str = "", citations: str = "") -> str:
        prompt = PROMPT_TEMPLATE.format(
            context=context,
            citations=citations or "None provided",
            graph_context=graph_context or "None"
        )
        raw = self.llm.generate(prompt)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {
                "evidence_strength": "weak",
                "logical_gaps": [],
                "citation_count": 0,
                "confidence": 0.4,
                "summary": raw[:200]
            }

        confidence = float(data.get("confidence", 0.4))
        citation_count = int(data.get("citation_count", 0))

        flags = []
        if confidence < WEAK_EVIDENCE_THRESHOLD:
            flags.append(FlagType.WEAK_EVIDENCE)
        if citation_count < MIN_CITATION_COUNT:
            flags.append(FlagType.CITATION_GAP)

        node_type = NodeType.FLAG if flags else NodeType.DECISION

        node = GraphNode(
            id="",
            agent=AgentName.LOGICIAN,
            node_type=node_type,
            summary=data.get("summary", "Evidence evaluated by Logician."),
            confidence=confidence,
            flags=flags,
            output_artifact=json.dumps({
                "evidence_strength": data.get("evidence_strength"),
                "logical_gaps":      data.get("logical_gaps", []),
                "citation_count":    citation_count
            }, indent=2)
        )
        return self._add_to_graph(node)
