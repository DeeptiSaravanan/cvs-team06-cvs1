# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Aura Simulator — A/B Test Simulation Agent

Multi-agent architecture:
  1. audience_analyst      — segments target audience, sizes groups
  2. content_indexer       — ranks content repository for the use case
  3. experiment_runner     — runs Monte Carlo A/B simulations across holdout %s
  4. recommendation_agent  — synthesises results, picks best combination
  5. root_agent (orchestrator) — drives the full pipeline end-to-end
"""

import os

import google.auth
from google.adk.agents import Agent, SequentialAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StdioConnectionParams,
    StdioServerParameters,
)

from aura_simulator.tools.simulation_tools import (
    analyze_target_audience,
    filter_patients_by_usecase,
    find_best_ab_combination,
    index_content_repository,
    load_experiment_data,
    prepare_campaign_recipients,
    run_ab_test_simulation,
    save_results_csv,
)

# ---------------------------------------------------------------------------
# GCP auth bootstrapping
# ---------------------------------------------------------------------------
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

_MODEL = Gemini(
    model="gemini-flash-latest",
    retry_options=types.HttpRetryOptions(attempts=3),
)

# ---------------------------------------------------------------------------
# Sub-agent 0: Data Analyst — filters patients by use-case disease area
# ---------------------------------------------------------------------------
data_analyst = Agent(
    name="data_analyst",
    model=_MODEL,
    instruction="""You are the data analyst agent for Aura Simulator.

Your job — given the user's use case, load and filter the experiment data:
1. Call `filter_patients_by_usecase(use_case)` with the exact use-case text the user provided.
2. If it returns an error, display it clearly and stop the pipeline.
3. If successful, display a brief data-intake report:

   **Data Analyst Report**
   - Use case detected disease areas: list detected_disease_areas (or "None — all patients returned")
   - Filter applied: filter_reason
   - Patients retained: total_patients_after_filter / total_patients_before_filter
   - Audience segments: list each segment_name with its scaled size
   - Content items loaded: count

4. Do NOT run simulations or analyse content. Just confirm the data and pass it forward.

End with "Data Ready ✓".
""",
    tools=[filter_patients_by_usecase],
)

# ---------------------------------------------------------------------------
# Sub-agent 1: Audience Analyst
# ---------------------------------------------------------------------------
audience_analyst = Agent(
    name="audience_analyst",
    model=_MODEL,
    instruction="""You are an expert audience strategist specialising in A/B test design.

Your job depends on what the data_analyst returned in the conversation context:

**Case A — patient_segments are present (patient-level data loaded):**
  - Use the `patient_segments` list directly from the data_analyst output. Do NOT call `analyze_target_audience`.
  - Present the segments in a table with columns:
    Segment | Sample Patients | Scaled Size | Avg Age | Conversion Baseline | Engagement | Avg Copay | Disease Areas
  - Identify the best 1–2 segments for testing (highest conversion_baseline × engagement_propensity).
  - Note the total scaled audience size and any filter that was applied (e.g. "Diabetic patients only").

**Case B — no patient_segments (plain description loaded):**
  - Call `analyze_target_audience(audience_description, use_case)` using the description from the data_analyst.
  - Present the generated segments in a table.
  - Identify which segment(s) are most suitable for experimentation.

In both cases, end with "Audience Ready ✓".
""",
    tools=[analyze_target_audience],
)

# ---------------------------------------------------------------------------
# Sub-agent 2: Content Indexer
# ---------------------------------------------------------------------------
content_indexer = Agent(
    name="content_indexer",
    model=_MODEL,
    instruction="""You are a content strategist expert in matching content to audience use cases.

Your job:
1. Read the list of content items loaded by the data_loader from the conversation context.
2. Call `index_content_repository` with those content items and the use case from the user.
3. Display the ranked content table: ID, title, type, relevance score, estimated CTR.
4. Highlight the top 3 content variants you recommend testing.
5. Explain briefly WHY each top variant is likely to perform well for this use case.

Be concise. Use tables. End with "Content Indexed ✓".
""",
    tools=[index_content_repository],
)

# ---------------------------------------------------------------------------
# Sub-agent 3: Experiment Runner
# ---------------------------------------------------------------------------
experiment_runner = Agent(
    name="experiment_runner",
    model=_MODEL,
    instruction="""You are an A/B testing statistician running systematic experiments.

Your job:
1. For each of the top content variants (up to 3) provided in the conversation context:
   For each holdout percentage in [10%, 20%, 30%, 50%]:
     Call `run_ab_test_simulation` using:
       - The audience segment name and size from the context
       - The baseline_conversion from the audience analysis
       - The content_variant_id and relevance_score from the content index
       - The current holdout_pct
       - The use_case from context

2. After all simulations complete, call `find_best_ab_combination` with ALL results as a list.

3. Display a clear results table with columns:
   Variant | Holdout % | Lift % | Confidence % | Significant? | Score

4. State the single best combination clearly before the full table.

Be systematic. Run ALL simulations before calling find_best_ab_combination.
End with "Simulations Complete ✓".
""",
    tools=[run_ab_test_simulation, find_best_ab_combination],
)

# ---------------------------------------------------------------------------
# Sub-agent 4: Recommendation Agent
# ---------------------------------------------------------------------------
recommendation_agent = Agent(
    name="recommendation_agent",
    model=_MODEL,
    instruction="""You are a senior growth strategist delivering final A/B test recommendations.

Your job — synthesise all previous analysis into a crisp, actionable report, then save the results:

## 📊 Aura A/B Test Simulation Report

### 1. Executive Summary
- Best email message variant + recommended holdout %
- Expected lift and statistical confidence
- Estimated incremental refill conversions (lift × audience size)

### 2. Winning Combination
| Field | Value |
|-------|-------|
| Message Variant | ... |
| Holdout % | ... |
| Target Segment | ... |
| Expected Lift | ... |
| Confidence | ... |
| Statistically Significant | ... |

### 3. Winning Email Message
Display the full text of the winning email message from the content index context.
Explain in 2–3 sentences WHY this message is likely to drive the highest refill adherence
for this patient segment (referencing disease area, nudge type, copay, and persistence data).

### 4. Runner-Up Messages
Show top 2 alternative messages with their lift and a brief reasoning sentence each.

### 5. Implementation Roadmap
Step-by-step: when and how to send these messages, holdout group setup, and criteria to call a winner.

### 6. Risk & Caveats
Mention holdout size sensitivity, simulation assumptions (10,000× scale factor), and recommended real-world validation.

### 7. Save Results
After completing the report, call `save_results_csv` with:
  - best_variant_id: the winning variant ID (e.g. 'content_001')
  - winning_message: the FULL TEXT of the winning email message (not truncated)
  - holdout_pct: the winning holdout fraction as a float (e.g. 0.30 for 30%)
Then confirm: "✅ Results saved to output/ab_test_results.csv — {test} test rows, {control} control rows."

Be professional. Reference actual simulation numbers and quote the email message text directly.
""",
    tools=[save_results_csv],
)

# ---------------------------------------------------------------------------
# Orchestrator — SequentialAgent drives the pipeline in order
# ---------------------------------------------------------------------------
pipeline = SequentialAgent(
    name="ab_test_pipeline",
    description="End-to-end A/B test simulation pipeline: filter data → audience → content → experiments → recommendation.",
    sub_agents=[
        data_analyst,      # Step 0: detect disease area, filter patients
        audience_analyst,  # Step 1: segment analysis
        content_indexer,   # Step 2: content relevance scoring
        experiment_runner, # Step 3: A/B simulations
        recommendation_agent,  # Step 4: winner + save CSV
    ],
)

# ---------------------------------------------------------------------------
# Execution Agent — triggered by user typing "execute" after reviewing results
# ---------------------------------------------------------------------------
# Gmail MCP server via npx — handles OAuth2 and delivery.
# Prerequisites (one-time setup):
#   1. npm / npx must be installed
#   2. Place your Google OAuth credentials.json at the path below
#   3. First run opens a browser for OAuth consent; token is cached automatically
_GMAIL_CREDENTIALS = os.environ.get(
    "GMAIL_CREDENTIALS_PATH",
    str(__file__.replace("agent.py", "../credentials/credentials.json")),
)

_gmail_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@gongrzhe/gmail-mcp-server"],
            env={
                **os.environ,
                "GMAIL_CREDENTIALS_PATH": _GMAIL_CREDENTIALS,
            },
        )
    )
)

execution_agent = Agent(
    name="execution_agent",
    model=_MODEL,
    instruction="""You are the campaign execution agent for Aura Simulator.

You are triggered ONLY when the user types "execute" (or similar: "send", "go", "launch").
This means they have reviewed the simulation report and are approving the campaign to go live.

Your job:
1. Call `prepare_campaign_recipients()` (no arguments) to load the test patient list from the
   latest simulation results CSV.
   - It returns: recipients (list of {patient_id, email, message}), control_count, email_subject.
   - If it returns an error, display it and stop.

2. For EACH recipient in the list, call the Gmail MCP `send_email` tool:
     to:      the recipient's email address
     subject: the email_subject returned in step 1
     body:    the recipient's message

3. After all emails are sent, display a summary:
   ✅ Campaign sent to {N} test patients | {control_count} in control (withheld)
   List each patient_id → email → ✅ sent / ❌ failed

4. End with: "✅ Campaign execution complete."

Do NOT re-run the simulation. Only send to the already-saved test recipients.
Do NOT send to control patients — they are the holdout group.
""",
    tools=[prepare_campaign_recipients, _gmail_mcp],
)

# ---------------------------------------------------------------------------
# Root agent — entry point, parses user input and kicks off pipeline
# ---------------------------------------------------------------------------
root_agent = Agent(
    name="aura_simulator",
    model=_MODEL,
    instruction="""You are Aura Simulator — an intelligent A/B test simulation engine powered by Google ADK.

The target audience and content repository are pre-loaded from files in the data/ folder.

You have TWO operating modes:

**Mode 1 — Simulate** (default)
  Triggered by: any use-case description (e.g. "improve refill adherence").
  Action: hand off to `ab_test_pipeline`.
  The pipeline will: load data → analyse audience → index content → simulate → recommend + save CSV.

**Mode 2 — Execute** (must be explicitly approved)
  Triggered by: the user typing "execute", "send", "go", or "launch".
  Action: hand off to `execution_agent`.
  The agent will read the latest saved results CSV and send emails to all 'test' patients.

If the user has not provided a use case yet, greet them warmly:
  "I automatically load your audience profile and content library from the data/ folder.
  Tell me the goal of your experiment and I'll run the full A/B simulation.
  Once you've reviewed the results, type **execute** to send the winning message to your test patients."

Do NOT ask for audience or content — those come from the files.
Do NOT execute automatically — always wait for the user to type "execute".
""",
    sub_agents=[pipeline, execution_agent],
)

app = App(
    root_agent=root_agent,
    name="aura_simulator",
)
