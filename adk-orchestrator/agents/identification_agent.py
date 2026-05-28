"""Identification Agent — Stub

Takes a health_concern string and returns matching member profiles.
This is a placeholder; the real implementation will query a data source.
"""

from google.adk.agents import LlmAgent

identification_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="identification_agent",
    description=(
        "Identifies CVS Health members matching a given health concern. "
        "Returns member profiles with xtra_card_nbr, demographics, and persona details."
    ),
    instruction="""You are the Identification Agent.

Given a health_concern, return a JSON list of matching member profiles.

For now, return MOCK data with this structure:
[
  {
    "xtra_card_nbr": "1001",
    "age": 45,
    "gender": "F",
    "health_concern": "<the concern>",
    "persona": "Active manager, frequent pharmacy visits, prefers digital communication",
    "risk_score": 0.72
  },
  ...
]

Return 3-5 mock members. Make the personas realistic and varied.
""",
)
