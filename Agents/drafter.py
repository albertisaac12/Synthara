import json
from Agents.base_agent import BaseAgent
from Core.graph_schema import GraphNode
from Core.Classtype import AgentName, NodeType


PROMPT_TEMPLATE = """\
You are the Drafter agent in a multi-agent research pipeline called Synthara.
Your job is to write a clear, well-structured academic research paragraph based on the evidence.

Claim:
{claim}

Logician's evaluation:
{logician_output}

Citations available:
{citations}

Prior pipeline context:
{graph_context}

Write a research paragraph of exactly 150–200 words that:
- Opens with the claim
- Cites 2–3 of the provided sources inline (Author, Year)
- Acknowledges any logical gaps noted by the Logician
- Ends with a concise conclusion

Respond in this exact JSON format (no markdown wrapper, no extra text):
{{
  "paragraph": "<the full research paragraph>",
  "word_count": <integer>,
  "confidence": <float 0.0–1.0>,
  "summary": "<One sentence describing what you wrote>"
}}
"""


class DrafterAgent(BaseAgent):
    """
    Composes the initial research paragraph based on the claim,
    evidence, and Logician evaluation.
    """

    def run(self, context: str, graph_context: str = "",
            logician_output: str = "", citations: str = "") -> str:
        prompt = PROMPT_TEMPLATE.format(
            claim=context,
            logician_output=logician_output or "Not available",
            citations=citations   or "Not available",
            graph_context=graph_context or "None"
        )
        raw = self.llm.generate(prompt)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {
                "paragraph":  raw,
                "word_count": len(raw.split()),
                "confidence": 0.6,
                "summary":    "Initial draft written."
            }

        node = GraphNode(
            id="",
            agent=AgentName.DRAFTER,
            node_type=NodeType.OUTPUT,
            summary=data.get("summary", "Draft written."),
            confidence=float(data.get("confidence", 0.6)),
            output_artifact=data.get("paragraph", raw)
        )
        return self._add_to_graph(node)
