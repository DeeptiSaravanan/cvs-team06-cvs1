import pandas as pd

def get_mock_personas_for_health_concern(concern: str) -> pd.DataFrame:
    """Returns a mock dataframe of users matching a health concern."""
    if "diabetes" in concern.lower():
        data = [
            {"user_id": "u101", "name": "Alice Smith", "age": 55, "concern": "diabetes type 2", "persona": "health_conscious_senior"},
            {"user_id": "u102", "name": "Bob Jones", "age": 42, "concern": "diabetes type 1", "persona": "busy_professional"},
        ]
    else:
        data = [
            {"user_id": "u999", "name": "Unknown", "age": 30, "concern": concern, "persona": "generic"}
        ]
    return pd.DataFrame(data)
