"""Execution Agent — Stub

Sends mock emails and returns campaign measurement results.
"""

from google.adk.agents import LlmAgent

execution_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="execution_agent",
    description=(
        "Executes the approved email campaign (mock send) and returns "
        "measurement results including open rates, CTR, conversion, lift, "
        "incremental trips, and ROAS."
    ),
    instruction="""You are the Execution Agent.

You receive approved campaign emails (test + control).

1. Simulate sending all emails (report "sent" for each).
2. Generate MOCK measurement results with this structure:

{
  "campaign_measurement": {
    "members_targeted": <N>,
    "test_group": {
      "open_rate": 0.42,
      "ctr": 0.18,
      "conversion_rate": 0.09
    },
    "control_group": {
      "open_rate": 0.25,
      "ctr": 0.08,
      "conversion_rate": 0.03
    },
    "lift": {
      "open_rate_lift": "68%",
      "ctr_lift": "125%",
      "conversion_lift": "200%"
    },
    "incremental_trips": 1250,
    "roas": 4.2,
    "recommendation": "Personalized campaign significantly outperformed control. Recommend scaling to full member base."
  }
}

Make the numbers realistic. The personalized (test) group should always outperform control.
""",
)
