# Gmail MCP — One-Time Setup

The execution agent uses `@gongrzhe/gmail-mcp-server` (via `npx`) to send emails
through your Gmail account using OAuth 2.0. Follow these steps once.

---

## Prerequisites

- Node.js ≥ 18 with `npx` available
- A Google account to send from

---

## Step 1 — Create a Google Cloud Project & enable Gmail API

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or reuse your existing Aura project)
3. Navigate to **APIs & Services → Library**
4. Search for **Gmail API** → Enable it

---

## Step 2 — Create OAuth 2.0 credentials

1. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. Application type: **Desktop app**
3. Name it: `Aura Simulator Gmail`
4. Click **Create** → **Download JSON**
5. Rename the downloaded file to `credentials.json`
6. **Place it in this folder** (`credentials/credentials.json`)

> ⚠️  Never commit `credentials.json` or `token.json` to version control.

---

## Step 3 — Run the auth flow (one-time)

The first time the execution agent runs, `npx @gongrzhe/gmail-mcp-server` will
open a browser window asking you to authorise the app.

- Select your Gmail account
- Grant the **Send mail** permission
- The token is saved automatically to `~/.gmail-mcp/token.json`

All subsequent runs reuse the cached token — no browser needed.

---

## Step 4 — Optional: custom credentials path

By default the agent looks for:
```
credentials/credentials.json   (relative to agent.py)
```

To use a different path:
```bash
export GMAIL_CREDENTIALS_PATH=/path/to/your/credentials.json
```

---

## What gets sent

When the user types **execute** in the chat, the agent:
1. Reads the latest `output/ab_test_results_*.csv`
2. Filters rows where `group == "test"`
3. Sends **one personalised email per patient** using their `email` and `best_content`
4. Reports success/failure per recipient

Control patients are **never emailed** — they are the holdout group.
