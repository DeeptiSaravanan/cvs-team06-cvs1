"""AURA Multi-Agent System — Entry Point

Runs the ADK-based healthcare campaign orchestrator.
Can be used with `adk run backend` or executed directly for testing.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import root_agent


def main():
    print("Welcome to the AURA Multi-Agent System")
    print(f"Root agent: {root_agent.name}")
    print(f"Model: {root_agent.model}")
    print(f"Tools: {[t.name if hasattr(t, 'name') else str(t) for t in root_agent.tools]}")
    print()
    print("To run interactively, use:  adk run backend")
    print("Or use the ADK web UI:      adk web backend")


if __name__ == "__main__":
    main()
