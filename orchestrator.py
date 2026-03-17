import json
from Core.graph_manager import GraphManager
from LLM.llm_client import LLMClient
from Agents.architect  import ArchitectAgent
from Agents.librarian  import LibrarianAgent
from Agents.logician   import LogicianAgent
from Agents.drafter    import DrafterAgent
from Agents.humanizer  import HumanizerAgent
from Agents.auditor    import AuditorAgent
from Core.Classtype    import FlagType
from config import SESSION_OUTPUT, MAX_RETRIES


class SyntharaOrchestrator:
    """
    Coordinates the full Synthara agent pipeline:
      Architect → Librarian → Logician → Drafter → Humanizer → Auditor

    Handles one correction loop:
      - If Logician flags WEAK_EVIDENCE / CITATION_GAP  → re-runs Librarian
      - If Auditor flags AUDIT_FAIL                     → re-runs Drafter + Humanizer

    Every agent action is recorded as a node in the shared GraphManager DAG.
    The session is exported to JSON at the end of the run.
    """

    def __init__(self):
        self.gm  = GraphManager()
        self.llm = LLMClient()

        # Instantiate agents
        self.architect  = ArchitectAgent (self.gm, self.llm)
        self.librarian  = LibrarianAgent (self.gm, self.llm)
        self.logician   = LogicianAgent  (self.gm, self.llm)
        self.drafter    = DrafterAgent   (self.gm, self.llm)
        self.humanizer  = HumanizerAgent (self.gm, self.llm)
        self.auditor    = AuditorAgent   (self.gm, self.llm)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _node_data(self, node_id: str):
        return self.gm.graph.nodes[node_id]["data"]

    def _log(self, step: str, node_id: str, summary: str):
        print(f"  [{step:<12}] {node_id}  —  {summary}")

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def run(self, claim: str) -> dict:
        print("\n" + "=" * 60)
        print(f"  SYNTHARA PIPELINE  |  Claim: {claim[:60]}...")
        print("=" * 60)

        # ── Step 1: Architect ──────────────────────────────────────────
        print("\n[1/6] Architect — structuring the claim...")
        arc_id = self.architect.run(context=claim)
        arc_node = self._node_data(arc_id)
        self._log("ARCHITECT", arc_id, arc_node.summary)

        # ── Step 2: Librarian ──────────────────────────────────────────
        print("\n[2/6] Librarian — retrieving citations...")
        lib_context    = arc_node.output_artifact or claim
        lib_graph_ctx  = self.gm.get_context_summary(arc_id)
        lib_id         = self.librarian.run(context=lib_context, graph_context=lib_graph_ctx)
        lib_node       = self._node_data(lib_id)
        self.gm.graph.nodes[lib_id]["data"].inputs = [arc_id]
        self.gm.graph.add_edge(arc_id, lib_id, type="input")
        self._log("LIBRARIAN", lib_id, lib_node.summary)

        citations_raw  = lib_node.output_artifact or ""

        # ── Step 3: Logician ───────────────────────────────────────────
        print("\n[3/6] Logician — evaluating evidence...")
        log_graph_ctx  = self.gm.get_context_summary(lib_id)
        log_id         = self.logician.run(
            context=lib_context,
            graph_context=log_graph_ctx,
            citations=citations_raw
        )
        log_node = self._node_data(log_id)
        self.gm.graph.nodes[log_id]["data"].inputs = [lib_id]
        self.gm.graph.add_edge(lib_id, log_id, type="input")
        self._log("LOGICIAN", log_id, log_node.summary)

        # Correction loop — re-run Librarian if evidence is flagged
        for retry in range(MAX_RETRIES):
            if not log_node.flags:
                break
            print(f"\n  ↩  Logician flagged {[f.value for f in log_node.flags]}. "
                  f"Retry {retry + 1}/{MAX_RETRIES}: re-running Librarian...")
            old_lib_id = lib_id
            lib_id = self.librarian.run(
                context=lib_context + "\n\n[RETRY — address these gaps: "
                        + ", ".join(f.value for f in log_node.flags) + "]",
                graph_context=self.gm.get_context_summary(log_id)
            )
            lib_node = self._node_data(lib_id)
            self.gm.graph.add_edge(log_id, lib_id, type="input")
            self.gm.supersede(old_lib_id, lib_id)
            citations_raw = lib_node.output_artifact or ""
            self._log("LIBRARIAN↩", lib_id, lib_node.summary)

            # Re-run Logician
            old_log_id = log_id
            log_id = self.logician.run(
                context=lib_context,
                graph_context=self.gm.get_context_summary(lib_id),
                citations=citations_raw
            )
            log_node = self._node_data(log_id)
            self.gm.graph.add_edge(lib_id, log_id, type="input")
            self.gm.supersede(old_log_id, log_id)
            self._log("LOGICIAN↩", log_id, log_node.summary)

        # ── Step 4: Drafter ────────────────────────────────────────────
        print("\n[4/6] Drafter — writing research paragraph...")
        dra_graph_ctx = self.gm.get_context_summary(log_id)
        dra_id = self.drafter.run(
            context=claim,
            graph_context=dra_graph_ctx,
            logician_output=log_node.output_artifact or "",
            citations=citations_raw
        )
        dra_node = self._node_data(dra_id)
        self.gm.graph.nodes[dra_id]["data"].inputs = [log_id]
        self.gm.graph.add_edge(log_id, dra_id, type="input")
        self._log("DRAFTER", dra_id, dra_node.summary)

        draft_paragraph = dra_node.output_artifact or ""

        # ── Step 5: Humanizer ──────────────────────────────────────────
        print("\n[5/6] Humanizer — polishing the paragraph...")
        hum_graph_ctx = self.gm.get_context_summary(dra_id)
        hum_id = self.humanizer.run(
            context=draft_paragraph,
            graph_context=hum_graph_ctx
        )
        hum_node = self._node_data(hum_id)
        self.gm.graph.nodes[hum_id]["data"].inputs = [dra_id]
        self.gm.graph.add_edge(dra_id, hum_id, type="input")
        self._log("HUMANIZER", hum_id, hum_node.summary)

        polished_paragraph = hum_node.output_artifact or draft_paragraph

        # ── Step 6: Auditor ────────────────────────────────────────────
        print("\n[6/6] Auditor — running quality audit...")
        aud_graph_ctx = self.gm.get_context_summary(hum_id)
        aud_id = self.auditor.run(
            context=polished_paragraph,
            graph_context=aud_graph_ctx,
            claim=claim,
            citations=citations_raw
        )
        aud_node = self._node_data(aud_id)
        self.gm.graph.nodes[aud_id]["data"].inputs = [hum_id]
        self.gm.graph.add_edge(hum_id, aud_id, type="input")
        self._log("AUDITOR", aud_id, aud_node.summary)

        # Correction loop — re-run Drafter + Humanizer if audit fails
        for retry in range(MAX_RETRIES):
            if self.auditor.last_verdict == "PASS":
                break
            print(f"\n  ↩  Auditor FAIL (score={self.auditor.last_score:.2f}). "
                  f"Retry {retry + 1}/{MAX_RETRIES}: re-drafting...")

            recommendation = self.auditor.last_recommendation
            old_dra_id = dra_id
            dra_id = self.drafter.run(
                context=claim + f"\n\n[REVISION REQUIRED: {recommendation}]",
                graph_context=self.gm.get_context_summary(aud_id),
                logician_output=log_node.output_artifact or "",
                citations=citations_raw
            )
            self.gm.graph.add_edge(aud_id, dra_id, type="input")
            self.gm.supersede(old_dra_id, dra_id)
            dra_node = self._node_data(dra_id)
            draft_paragraph = dra_node.output_artifact or ""
            self._log("DRAFTER↩", dra_id, dra_node.summary)

            old_hum_id = hum_id
            hum_id = self.humanizer.run(
                context=draft_paragraph,
                graph_context=self.gm.get_context_summary(dra_id)
            )
            self.gm.graph.add_edge(dra_id, hum_id, type="input")
            self.gm.supersede(old_hum_id, hum_id)
            hum_node = self._node_data(hum_id)
            polished_paragraph = hum_node.output_artifact or draft_paragraph
            self._log("HUMANIZER↩", hum_id, hum_node.summary)

            old_aud_id = aud_id
            aud_id = self.auditor.run(
                context=polished_paragraph,
                graph_context=self.gm.get_context_summary(hum_id),
                claim=claim,
                citations=citations_raw
            )
            self.gm.graph.add_edge(hum_id, aud_id, type="input")
            self.gm.supersede(old_aud_id, aud_id)
            aud_node = self._node_data(aud_id)
            self._log("AUDITOR↩", aud_id, aud_node.summary)

        # ── Export session ─────────────────────────────────────────────
        self.gm.export_session(SESSION_OUTPUT)
        flagged = self.gm.get_flagged_nodes()

        print("\n" + "=" * 60)
        print("  PIPELINE COMPLETE")
        print("=" * 60)

        return {
            "output":        polished_paragraph,
            "session_file":  SESSION_OUTPUT,
            "audit_score":   getattr(self.auditor, "last_score", None),
            "audit_verdict": getattr(self.auditor, "last_verdict", None),
            "flagged_nodes": [n.id for n in flagged],
            "total_nodes":   self.gm.graph.number_of_nodes()
        }
