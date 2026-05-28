"""Execution Agent — ADK LlmAgent

Sends mock emails and returns campaign measurement results.
Uses a FunctionTool to simulate sending and gather metrics.
"""

import json
import random
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool


def execute_and_measure(recipient_count: int) -> str:
    """Execute the campaign (mock send) and return measurement results.

    Args:
        recipient_count: The total number of members targeted in the campaign.

    Returns:
        A JSON string containing campaign measurement results including
        open rates, CTR, conversion, lift, incremental trips, and ROAS.
    """
    # Generate realistic mock metrics where test outperforms control
    test_open = round(random.uniform(0.35, 0.50), 2)
    test_ctr = round(random.uniform(0.12, 0.22), 2)
    test_conv = round(random.uniform(0.06, 0.12), 2)

    control_open = round(random.uniform(0.18, 0.28), 2)
    control_ctr = round(random.uniform(0.04, 0.10), 2)
    control_conv = round(random.uniform(0.02, 0.05), 2)

    open_lift = round((test_open - control_open) / control_open * 100)
    ctr_lift = round((test_ctr - control_ctr) / control_ctr * 100)
    conv_lift = round((test_conv - control_conv) / control_conv * 100)

    incremental_trips = random.randint(800, 2000)
    roas = round(random.uniform(3.0, 6.0), 1)

    results = {
        "campaign_measurement": {
            "members_targeted": recipient_count,
            "test_group": {
                "open_rate": test_open,
                "ctr": test_ctr,
                "conversion_rate": test_conv,
            },
            "control_group": {
                "open_rate": control_open,
                "ctr": control_ctr,
                "conversion_rate": control_conv,
            },
            "lift": {
                "open_rate_lift": f"{open_lift}%",
                "ctr_lift": f"{ctr_lift}%",
                "conversion_lift": f"{conv_lift}%",
            },
            "incremental_trips": incremental_trips,
            "roas": roas,
            "recommendation": (
                "Personalized campaign significantly outperformed control. "
                "Recommend scaling to full member base."
            ),
        }
    }
    return json.dumps(results, indent=2)


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

1. Acknowledge that all emails have been sent (mock).
2. Call execute_and_measure with the total recipient count to get campaign metrics.
3. Return the full measurement results exactly as provided by the tool.

Do not fabricate metrics — use the tool output.
""",
    tools=[FunctionTool(execute_and_measure)],
)
