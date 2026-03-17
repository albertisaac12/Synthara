import json
from Agents.base_agent import BaseAgent
from Core.graph_schema import GraphNode
from Core.Classtype import AgentName, NodeType


PROMPT_TEMPLATE = """\
You are the Architect agent in a multi-agent research pipeline called Synthara.
Your job is to analyse the user's raw claim and produce a structured breakdown.

Claim: {claim}

Prior context from the pipeline graph:
{graph_context}

Respond in this exact JSON format (no markdown, no extra text):
{{
  "claim_type": "<exploratory | argumentative | factual>",
  "refined_claim": "<a single, precise version of the claim>",
  "sub_questions": ["<question 1>", "<question 2>", "<question 3>"],
  "confidence": <float between 0.0 and 1.0>,
  "summary": "<one sentence summary of your analysis>"
}}
"""


class ArchitectAgent(BaseAgent):
    """
    First agent in the pipeline.
    Classifies the claim, refines it, and identifies sub-questions.
    """

    def run(self, context: str, graph_context: str = "") -> str:
        prompt = PROMPT_TEMPLATE.format(claim=context, graph_context=graph_context or "None")
        raw = self.llm.generate(prompt)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback if model returns non-JSON
            data = {
                "claim_type": "exploratory",
                "refined_claim": context,
                "sub_questions": [],
                "confidence": 0.7,
                "summary": raw[:200]
            }

        structured_output = json.dumps({
            "claim_type":    data.get("claim_type", "exploratory"),
            "refined_claim": data.get("refined_claim", context),
            "sub_questions": data.get("sub_questions", [])
        }, indent=2)

        node = GraphNode(
            id="",
            agent=AgentName.ARCHITECT,
            node_type=NodeType.DECISION,
            summary=data.get("summary", "Claim structured by Architect."),
            confidence=float(data.get("confidence", 0.7)),
            output_artifact=structured_output
        )
        return self._add_to_graph(node)
