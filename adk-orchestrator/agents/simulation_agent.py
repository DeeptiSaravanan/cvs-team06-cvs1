"""Simulation Agent — Stub

Takes member profiles + channel and produces personalized emails (test)
and generic emails (control), then validates via a guardrail.
Internally would use PersonaTestAgent + PersonaControlAgent in parallel.
This is a placeholder.
"""

from google.adk.agents import LlmAgent

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

For each member, generate TWO email variants:
1. **test_email** (personalized) — tailored to the member's persona, age, health concern.
2. **control_email** (generic) — a standard, non-personalized version.

Return your output as JSON with this structure:
{
  "test_emails": [
    {
      "xtra_card_nbr": "1001",
      "subject": "Personalized subject line",
      "body": "Personalized email body (2-3 sentences)"
    }
  ],
  "control_emails": [
    {
      "xtra_card_nbr": "1001",
      "subject": "Generic subject line",
      "body": "Generic email body (2-3 sentences)"
    }
  ]
}

Make the personalized versions noticeably more relevant than the generic ones.
""",
)
