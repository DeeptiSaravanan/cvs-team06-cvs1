import pandas as pd
import random

class ExecutionAgent:
    def __init__(self):
        pass
        
    def execute_campaign(self, interventions_df: pd.DataFrame) -> dict:
        """
        Sends the emails and does some measurement on how efficient the campaign was in real-time.
        Returns the measurement back.
        """
        print("[Execution Agent] Executing campaign (mock sending emails)...")
        for _, row in interventions_df.iterrows():
            print(f"   -> Sending to {row['user_id']}: {row['email_text']}")
            
        print("[Execution Agent] Gathering metrics...")
        # Mock metrics
        metrics = {
            "total_sent": len(interventions_df),
            "open_rate_estimate": round(random.uniform(0.1, 0.4), 2),
            "click_rate_estimate": round(random.uniform(0.01, 0.1), 2)
        }
        return metrics
