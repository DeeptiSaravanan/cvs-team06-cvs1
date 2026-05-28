"""Identification Agent — ADK LlmAgent

Takes a health_concern string and returns matching member profiles.
Uses the existing mock data utility as a FunctionTool so the real
data-lookup logic is preserved.
"""

import json
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from backend.utils.mock_data import get_mock_personas_for_health_concern


def identify_members(health_concern: str) -> str:
    """Look up CVS Health members matching a given health concern.

    Args:
        health_concern: The health condition to search for
            (e.g. "diabetes", "heart health", "respiratory").

    Returns:
        A JSON string of matching member profiles with xtra_card_nbr,
        demographics, and persona details.
    """
    df = get_mock_personas_for_health_concern(health_concern)
    return df.to_json(orient="records", indent=2)


identification_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="identification_agent",
    description=(
        "Identifies CVS Health members matching a given health concern. "
        "Returns member profiles with xtra_card_nbr, demographics, and persona details."
    ),
    instruction="""You are the Identification Agent.

When given a health_concern, call the identify_members tool to look up matching members.

Return the results exactly as provided by the tool — do not fabricate additional members.
Include a brief count summary, e.g. "Found N members matching '<concern>'."
""",
    tools=[FunctionTool(identify_members)],
)
