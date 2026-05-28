"""Execution Agent — Returns a mock campaign email and hardcoded metrics."""

import json
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool


def send_campaign_emails(simulation_result: str) -> str:
    """Mock-send campaign emails. Returns what would have been sent.

    Args:
        simulation_result: JSON from simulation (used for context).

    Returns:
        JSON with the mock email that would be sent.
    """
    return json.dumps({
        "total_sent": 1,
        "mock_recipient": "palakb1406@gmail.com",
        "email": {
            "subject": "Your Personalized Diabetes Care Plan from CVS Health",
            "body": (
                "Hi there,\n\n"
                "At CVS Health, we know managing diabetes is personal.\n\n"
                "Based on your pharmacy activity, here's your tailored care plan:\n"
                "  • Save 20% on glucose monitors & test strips\n"
                "  • FREE A1C screening at MinuteClinic\n"
                "  • Personalized medication reminders via the CVS app\n"
                "  • 90-day supply options to simplify refills\n\n"
                "Stay well,\nThe CVS Health Team"
            ),
        },
    }, indent=2)


def measure_campaign(total_sent: int) -> str:
    """Return hardcoded campaign metrics.

    Args:
        total_sent: Number of emails sent.

    Returns:
        JSON with campaign measurement.
    """
    return json.dumps({
        "members_targeted": total_sent,
        "test_group": {"open_rate": 0.42, "ctr": 0.18, "conversion": 0.09},
        "control_group": {"open_rate": 0.25, "ctr": 0.08, "conversion": 0.03},
        "lift": {"open_rate": "68%", "ctr": "125%", "conversion": "200%"},
        "incremental_trips": 1250,
        "roas": 4.2,
        "recommendation": "Personalized campaign outperformed control. Scale to full base.",
    }, indent=2)


execution_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="execution_agent",
    description="Mock-sends approved campaign emails and returns measurement results.",
    instruction="""You are the Execution Agent. Only run AFTER human approval.

1. Call send_campaign_emails with the simulation results.
2. Call measure_campaign with the total_sent from step 1.
3. Return both results.
""",
    tools=[FunctionTool(send_campaign_emails), FunctionTool(measure_campaign)],
)
