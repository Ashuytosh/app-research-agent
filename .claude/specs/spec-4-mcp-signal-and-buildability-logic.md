# Spec 4 — Dedicated MCP Signal + Corrected Buildability Logic

## Objective
Fix the two systematic errors found when testing spec 3 on the 5 CRM apps:
(1) has_mcp was always false because it was being extracted from the auth-docs page, which does not mention MCP servers — it needs its own search signal.
(2) buildability logic was wrong: the model treated "no MCP" as a reason for "needs-outreach", but MCP presence is irrelevant to buildability. Buildability depends only on auth + public API availability.

## Part A — MCP detection (`src/mcp_check.py`)
- New function `check_mcp(app_name: str) -> dict` returning `{"has_mcp": bool, "mcp_evidence_url": str}`.
- Run a Firecrawl search for a query like `f"{app_name} MCP server model context protocol"`.
- Decide has_mcp = true if a credible result indicates an official or well-known MCP server for that app (e.g. a result whose title/snippet/url clearly references an MCP server for the app, such as an mcp.<app>.com domain, an official docs page, or a recognized repo). Otherwise false.
- Capture the URL of the best supporting result as mcp_evidence_url (empty string if none).
- Never raise; on search failure return {"has_mcp": false, "mcp_evidence_url": ""}.
- Keep it cheap: one search per app, top few results only. Search only (1 credit), no scrape needed for this check.
- Log one line per app: app name, has_mcp decision, evidence url.

## Part B — Wire MCP into research (`src/research.py`)
- In research_one, after the main extraction, call check_mcp(app_name).
- Set has_mcp from check_mcp's result (override whatever the extraction model said — the model no longer decides this field).
- Optionally store mcp_evidence_url. If you don't want a new schema field, you may append it into main_blocker context only when relevant; simplest is to add an optional schema field `mcp_evidence_url: str = ""` in schema.py and populate it.

## Part C — Fix buildability logic in the prompt (`src/prompts.py`)
Replace the buildability guidance with an explicit decision rule the model must follow, in this order:
- "blocked" — there is no usable public API at all (no documented REST/GraphQL, or API access is impossible without an enterprise/partnership contract just to read docs).
- "needs-outreach" — a public API exists, BUT getting working credentials requires paid-only plans, manual admin approval, partnership, or a contact-sales/app-review gate before any real usage.
- "buildable-now" — a public API exists AND a developer can obtain working credentials themselves (free tier, trial, or self-serve key/OAuth app) without partnership or sales approval.
State explicitly: the existence or absence of an MCP server MUST NOT affect the buildability verdict. MCP is a convenience, not a requirement. Do not use "no MCP" as a blocker.
Also: main_blocker must describe a real credential/API access barrier, never "no MCP server".

## Part D — Schema note (`src/schema.py`)
- Add optional field `mcp_evidence_url: str = ""` with a short docstring. Keep all other fields unchanged.

## Conventions
- Reuse retriever, model_runner, input_loader, schema.
- One search per app for MCP; do not scrape for the MCP check.
- One-line purpose comment at top of new/changed files.

## Done when
- Re-running on the 5 CRM apps:
  - Attio has_mcp = true with a real mcp_evidence_url (Attio has an official MCP server).
  - HubSpot has_mcp = true (HubSpot has an MCP server), and its buildability is re-evaluated on auth/API grounds, not on MCP absence.
  - Pipedrive/Salesforce/Twenty buildability verdicts follow the explicit rule and no row uses "no MCP" as a blocker.
- MCP search failure on any app degrades to has_mcp=false without crashing.