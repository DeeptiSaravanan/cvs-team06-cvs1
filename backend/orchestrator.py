from backend.agents.identification_agent import IdentificationAgent
from backend.agents.simulation_agent import SimulationAgent
from backend.agents.execution_agent import ExecutionAgent

class Orchestrator:
    def __init__(self):
        self.identification_agent = IdentificationAgent()
        self.simulation_agent = SimulationAgent()
        self.execution_agent = ExecutionAgent()
        
    def run_flow(self, health_concern: str, channel: str):
        print("="*50)
        print(f"[Orchestrator] Starting workflow for concern='{health_concern}' on channel='{channel}'")
        print("="*50)
        
        # Step 1: Identification
        users_df = self.identification_agent.identify_users(health_concern)
        
        # Step 2: Simulation
        interventions_df = self.simulation_agent.simulate_interventions(channel, users_df)
        
        # Step 3: Human In The Loop (HITL)
        print("\n--- HUMAN IN THE LOOP APPROVAL ---")
        print("Proposed Interventions:")
        print(interventions_df)
        print("----------------------------------\n")
        
        # Mocking user input for approval. For a real app, this would be an API pause or websocket event.
        # Here we assume approval is granted for demonstration purposes when run as a script.
        approval = input("Approve sending these emails? (y/n) [default: y]: ")
        if approval.lower() == 'n':
            print("[Orchestrator] Campaign halted by Human-in-the-Loop.")
            return
            
        # Step 4: Execution
        metrics = self.execution_agent.execute_campaign(interventions_df)
        
        print("\n[Orchestrator] Campaign Complete. Results back to Orchestrator:")
        print(metrics)
        print("="*50)
        
        return metrics
