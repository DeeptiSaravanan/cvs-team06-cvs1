import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.orchestrator import Orchestrator

def main():
    print("Welcome to the AURA Multi-Agent System")
    orchestrator = Orchestrator()
    
    # Simulating the user input
    orchestrator.run_flow(health_concern="diabetes", channel="email")

if __name__ == "__main__":
    main()
