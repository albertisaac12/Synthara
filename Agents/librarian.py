import json
from Agents.base_agent import BaseAgent
from Core.graph_schema import GraphNode
from Core.Classtype import AgentName, NodeType


PROMPT_TEMPLATE = """\
You are the Librarian agent in a multi-agent research pipeline called Synthara.
Your job is to find relevant academic citations that support or challenge the claim.

Claim / Architect output:
{context}

Prior pipeline context:
{graph_context}

Generate exactly 4 plausible academic citations relevant to this claim.
Each citation must be realistic (author, year, journal, relevance note).
Respond in this exact JSON format (no markdown, no extra text):
{{
  "citations": [
    {{
      "authors": "<Last, F. and Last, F.>",
      "year": <year>,
      "title": "<Paper title>",
      "journal": "<Journal name>",
      "relevance": "<One sentence on why this supports or challenges the claim>"
    }}
  ],
  "confidence": <float 0.0–1.0>,
  "summary": "<One sentence summary of what you found>"
}}
"""


class LibrarianAgent(BaseAgent):
    """
    Retrieves (simulated) academic citations relevant to the claim.
    """

    def run(self, context: str, graph_context: str = "") -> str:
        prompt = PROMPT_TEMPLATE.format(context=context, graph_context=graph_context or "None")
        raw = self.llm.generate(prompt)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {
                "citations": [],
                "confidence": 0.5,
                "summary": raw[:200]
            }

        citations = data.get("citations", [])
        artifact = json.dumps({"citations": citations}, indent=2)

        node = GraphNode(
            id="",
            agent=AgentName.LIBRARIAN,
            node_type=NodeType.OUTPUT,
            summary=data.get("summary", f"Retrieved {len(citations)} citations."),
            confidence=float(data.get("confidence", 0.5)),
            output_artifact=artifact
        )
        return self._add_to_graph(node)
