import pandas as pd

class PersonaAgentTest:
    def generate_intervention(self, row, channel_type: str) -> str:
        return f"Mock {channel_type} [TEST]: Hi {row['name']}, check out our new program for your {row['concern']}!"

class PersonaAgentControl:
    def generate_intervention(self, row, channel_type: str) -> str:
        return f"Mock {channel_type} [CONTROL]: Information regarding {row['concern']} is available."

class SimulationAgent:
    def __init__(self):
        self.test_agent = PersonaAgentTest()
        self.control_agent = PersonaAgentControl()

    def simulate_interventions(self, channel_type: str, users_df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes the channel type and intervention and the DataFrame from identification.
        Returns a DataFrame of IDs and the text/email to be sent.
        """
        print(f"[Simulation Agent] Simulating '{channel_type}' interventions for {len(users_df)} users.")
        
        results = []
        # basic mock simulation: alternate test and control
        for idx, row in users_df.iterrows():
            if idx % 2 == 0:
                intervention_text = self.test_agent.generate_intervention(row, channel_type)
                group = "test"
            else:
                intervention_text = self.control_agent.generate_intervention(row, channel_type)
                group = "control"
                
            results.append({
                "user_id": row["user_id"],
                "group": group,
                "email_text": intervention_text
            })
            
        result_df = pd.DataFrame(results)
        return result_df
