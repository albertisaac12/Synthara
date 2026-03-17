import json
from Agents.base_agent import BaseAgent
from Core.graph_schema import GraphNode
from Core.Classtype import AgentName, NodeType


PROMPT_TEMPLATE = """\
You are the Humanizer agent in a multi-agent research pipeline called Synthara.
Your job is to polish a research paragraph so it reads naturally and avoids AI-sounding patterns.

Original paragraph from Drafter:
{draft}

Prior pipeline context:
{graph_context}

Rewrite the paragraph so that it:
- Sounds like it was written by a human researcher
- Removes AI-isms (e.g. "It is worth noting", "In conclusion", "Furthermore")
- Preserves all factual content and inline citations
- Maintains academic tone without being stiff
- Stays within 150–210 words

Respond in this exact JSON format (no markdown, no extra text):
{{
  "polished_paragraph": "<the rewritten paragraph>",
  "changes_made": ["<change 1>", "<change 2>"],
  "confidence": <float 0.0–1.0>,
  "summary": "<One sentence on what you changed>"
}}
"""


class HumanizerAgent(BaseAgent):
    """
    Polishes the Drafter's paragraph to sound natural and human-authored.
    """

    def run(self, context: str, graph_context: str = "") -> str:
        prompt = PROMPT_TEMPLATE.format(
            draft=context,
            graph_context=graph_context or "None"
        )
        raw = self.llm.generate(prompt)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {
                "polished_paragraph": context,
                "changes_made":       [],
                "confidence":         0.7,
                "summary":            "Humanization applied."
            }

        node = GraphNode(
            id="",
            agent=AgentName.HUMANIZER,
            node_type=NodeType.OUTPUT,
            summary=data.get("summary", "Paragraph humanized."),
            confidence=float(data.get("confidence", 0.7)),
            output_artifact=data.get("polished_paragraph", context)
        )
        return self._add_to_graph(node)
