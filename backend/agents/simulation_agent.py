"""Simulation Agent — ADK LlmAgent

Takes member profiles + channel and produces personalized emails (test)
and generic emails (control), then validates via a guardrail.
Uses the existing PersonaTestAgent + PersonaControlAgent logic as FunctionTools.
"""

import json
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool


def generate_test_email(name: str, concern: str, persona: str, channel: str) -> str:
    """Generate a personalized (test-group) email for a member.

    Args:
        name: The member's name.
        concern: The member's health concern.
        persona: The member's persona type.
        channel: The communication channel (e.g. "email").

    Returns:
        A personalized email string tailored to the member's profile.
    """
    return (
        f"Subject: {name}, your personalized {concern} care plan is ready\n\n"
        f"Hi {name},\n\n"
        f"As someone who values {persona.replace('_', ' ')} care, we've tailored a "
        f"{concern} management program just for you. Visit your nearest CVS to learn more "
        f"about exclusive savings on your prescriptions.\n\n"
        f"— CVS Health Team"
    )


def generate_control_email(name: str, concern: str, channel: str) -> str:
    """Generate a generic (control-group) email for a member.

    Args:
        name: The member's name.
        concern: The member's health concern.
        channel: The communication channel (e.g. "email").

    Returns:
        A generic, non-personalized email string.
    """
    return (
        f"Subject: Important health information from CVS Health\n\n"
        f"Dear Member,\n\n"
        f"Information regarding {concern} management is available at your local "
        f"CVS pharmacy. Visit us to learn about available programs.\n\n"
        f"— CVS Health"
    )


simulation_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="simulation_agent",
    description=(
        "Simulates a personalized email campaign. Generates test (personalized) "
        "and control (generic) email variants for each identified member. "
        "Returns test_emails and control_emails lists."
    ),
    instruction="""You are the Simulation Agent.

You receive member profiles and a channel type (e.g. "email").

For each member, generate TWO email variants using the provided tools:
1. Call generate_test_email for the personalized (test) variant.
2. Call generate_control_email for the generic (control) variant.

After generating all emails, return your output as JSON with this structure:
{
  "test_emails": [
    {
      "xtra_card_nbr": "<user_id>",
      "subject": "Personalized subject line",
      "body": "Personalized email body"
    }
  ],
  "control_emails": [
    {
      "xtra_card_nbr": "<user_id>",
      "subject": "Generic subject line",
      "body": "Generic email body"
    }
  ]
}

Make the personalized versions noticeably more relevant than the generic ones.
""",
    tools=[
        FunctionTool(generate_test_email),
        FunctionTool(generate_control_email),
    ],
)
