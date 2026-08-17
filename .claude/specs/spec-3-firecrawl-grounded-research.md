# Spec 3 — Search-Backed, Grounded Research (Firecrawl)

## Objective
Fix the two quality failures found when testing spec 2 on 5 apps: (1) plain requests fails on JS-heavy / blocked developer portals, leaving big apps unresearched, and (2) the LLM was allowed to invent the evidence URL. Replace the fetcher with a Firecrawl search-then-scrape retriever, and make the pipeline set the evidence URL from the actually-scraped page so it can never be fabricated.

## Setup
- FIRECRAWL_API_KEY is in .env. Load it via python-dotenv.
- Add `firecrawl-py` to requirements.txt and install it.
- Use ONLY Firecrawl Search and Scrape (1 credit/page). Do NOT enable JSON-extract mode, Enhanced mode, or the FIRE-1 agent — extraction is done by our own local/Gemini models. This keeps usage inside the free tier.

## Part A — Firecrawl retriever (`src/retriever.py`)
Replaces the role of the old fetcher. Provide:
- `search_and_scrape(app_name: str, hint_url: str) -> dict` that returns `{"url": <str>, "content": <str>}`:
  1. Run a Firecrawl search for a query like `f"{app_name} API authentication documentation"`.
  2. Prefer a result whose domain matches the hint_url's domain if present; otherwise take the top result.
  3. Scrape that result URL with Firecrawl, requesting markdown output.
  4. Return the scraped URL and its markdown content (trimmed to ~8000 chars).
  5. On any failure (no results, scrape error, empty content), fall back to scraping hint_url directly; if that also fails, return `{"url": hint_url, "content": ""}`.
- Never raise; always return the dict. Log one line per app: which URL was chosen and content length.

## Part B — Update research to ground evidence (`src/research.py`)
- `research_one` now calls `search_and_scrape` instead of the old fetcher.
- The prompt receives the scraped content only.
- CRITICAL: after the model returns its JSON, the pipeline OVERWRITES `evidence_url` with the URL that was actually scraped (`retriever_result["url"]`). The model's value for evidence_url is ignored entirely. This makes fabricated URLs impossible.
- Keep app_name, category, researched_by set from known inputs as before.
- If scraped content is empty, still produce a row with unknown/low-confidence values and evidence_url = the URL attempted.

## Part C — Tighten the prompt (`src/prompts.py`)
- Add explicit grounding instructions: use ONLY the provided content; if the content does not clearly state a field, return "unknown" (or false for has_mcp) and set confidence "low"; do NOT use outside/prior knowledge; do NOT guess.
- Remove any instruction that asks the model to produce evidence_url (code owns it now); the model may omit it.
- Keep the prompt-injection delimiter hardening from spec 2.

## Conventions
- Reuse schema, model_runner, input_loader unchanged.
- The old fetcher may be kept but is no longer used by research; retriever is the path.
- One-line purpose comment at top of each new/changed file.

## Done when
- Re-running `python src/run_research.py --model qwen2.5:7b` on the 5 CRM apps produces:
  - Salesforce and HubSpot now return real auth/API values (not all-unknown), because Firecrawl gets through.
  - every evidence_url points to a real page that was actually scraped (no invented domains).
  - Attio in particular resolves to real values with a real developers.attio.com-style evidence URL.
- A run where search returns nothing still degrades to an unknown/low row without crashing.