"""
main.py — Synthara CLI Entry Point

Usage:
    python main.py
    python main.py "Your research claim here"
    python main.py --claim "Your research claim here"
"""

import sys
import argparse
from orchestrator import SyntharaOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Synthara — Multi-Agent Research Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Climate change is primarily driven by human industrial activity"
  python main.py --claim "Quantum computing will obsolete RSA encryption by 2035"
        """
    )
    parser.add_argument(
        "claim",
        nargs="?",
        help="The research claim to run through the pipeline."
    )
    parser.add_argument(
        "--claim",
        dest="claim_flag",
        help="Alternative way to pass the claim."
    )
    args = parser.parse_args()

    claim = args.claim or args.claim_flag

    if not claim:
        print("Synthara — Multi-Agent Research Pipeline")
        print("-" * 42)
        claim = input("Enter a research claim: ").strip()
        if not claim:
            print("Error: No claim provided. Exiting.")
            sys.exit(1)

    orchestrator = SyntharaOrchestrator()
    result = orchestrator.run(claim)

    print("\n" + "─" * 60)
    print("  FINAL OUTPUT")
    print("─" * 60)
    print(result["output"])
    print("\n" + "─" * 60)
    print(f"  Audit Score   : {result['audit_score']:.2f}  |  "
          f"Verdict: {result['audit_verdict']}")
    print(f"  Total Nodes   : {result['total_nodes']}")
    print(f"  Flagged Nodes : {result['flagged_nodes'] or 'None'}")
    print(f"  Session saved : {result['session_file']}")
    print("─" * 60 + "\n")


if __name__ == "__main__":
    main()
