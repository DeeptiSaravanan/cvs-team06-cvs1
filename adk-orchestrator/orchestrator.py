"""Healthcare Campaign Orchestrator — Root Agent

Uses LlmAgent with sub-agents as tools to coordinate the full
Identification → Simulation → Approval → Execution pipeline.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool, FunctionTool

from agents.identification_agent import identification_agent
from agents.simulation_agent import simulation_agent
from agents.execution_agent import execution_agent
from tools.human_approval import human_approval


# ── Root Orchestrator ─────────────────────────────────────────────────────────

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="healthcare_campaign_orchestrator",
    description=(
        "End-to-end healthcare campaign orchestrator for CVS Health. "
        "Takes a health concern + channel, identifies members, simulates personalized "
        "emails, gets human approval, sends (mock), and returns measurement."
    ),
    instruction="""You are the Healthcare Campaign Orchestrator for CVS Health.

You run a 4-stage pipeline when a user requests a health campaign:

INPUT PARSING
  Extract from the user's message:
    - health_concern  (e.g. "diabetes", "heart health", "respiratory", "pain management")
    - channel         (default: "email" if not stated)

STAGE 1 — IDENTIFICATION
  Call identification_agent with the health_concern.
  It returns matching member profiles. Acknowledge the member count to the user.

STAGE 2 — SIMULATION
  Call simulation_agent with the member profiles and the channel.
  It runs PersonaTestAgent + PersonaControlAgent in parallel, then validates with
  a guardrail (up to 5 retries). When complete, briefly summarize what was generated.

STAGE 3 — HUMAN APPROVAL (REQUIRED)
  Before sending ANY email, call human_approval with a JSON preview:
  {
    "health_concern": "...",
    "channel": "email",
    "recipient_count": N,
    "email_samples": [
      {"xtra_card_nbr": "...", "subject": "...", "body": "..."}
    ]
  }
  Use the first 1–2 entries from test_emails for the samples.
  If the human rejects: STOP. Report the rejection and ask if they want to retry.
  If the human approves: proceed to Stage 4.

STAGE 4 — EXECUTION & MEASUREMENT
  Call execution_agent with the approved campaign data.
  Return the full campaign_measurement results to the user in a readable summary:
    - Members targeted
    - Personalized vs. control open rate, CTR, conversion
    - Lift percentages
    - Incremental trips
    - ROAS
    - Recommendation

GUARDRAIL RULE: Never skip human_approval. Never call execution_agent before approval.
""",
    tools=[
        AgentTool(agent=identification_agent),
        AgentTool(agent=simulation_agent),
        FunctionTool(human_approval),
        AgentTool(agent=execution_agent),
    ],
)
