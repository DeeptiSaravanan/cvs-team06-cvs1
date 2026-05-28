import pandas as pd
from backend.utils.mock_data import get_mock_personas_for_health_concern

class IdentificationAgent:
    def __init__(self):
        pass

    def identify_users(self, health_concern: str) -> pd.DataFrame:
        """
        Takes a health concern and gives back a user ID along with the persona of that patient.
        Returns a DataFrame.
        """
        print(f"[Identification Agent] Identifying users for health concern: '{health_concern}'")
        df = get_mock_personas_for_health_concern(health_concern)
        print(f"[Identification Agent] Found {len(df)} users.")
        return df
