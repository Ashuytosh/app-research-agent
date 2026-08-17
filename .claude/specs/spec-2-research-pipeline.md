# Spec 2 — Research Pipeline (fetch → extract → validate → save)

## Objective
Implement the core research loop: for each app in the input file, fetch its documentation, use an LLM to extract the research fields into the AppResearch schema, validate, and save results per model. Builds directly on spec 1 (schema, input_loader, model_runner).

## Part A — Fetcher (`src/fetcher.py`)
- `fetch_docs(url: str) -> str`: download the page with `requests` (set a browser-like User-Agent, 15s timeout), parse with BeautifulSoup, extract readable text (drop script/style/nav/footer), collapse whitespace.
- Trim output to a max character budget (default ~8000 chars) so it fits local model context. Add `max_chars` param.
- On any failure (timeout, 404, blocked), return an empty string — never raise. Caller handles empties.

## Part B — Extraction prompt (`src/prompts.py`)
- A function `build_research_prompt(app_name: str, category: str, doc_text: str) -> str`.
- The prompt must:
  - State the task: extract structured research about the app for building an agent toolkit.
  - List every AppResearch field with its allowed values (access_type, buildability, confidence enums; has_mcp boolean).
  - Instruct: return ONLY valid JSON, no markdown, no commentary.
  - Wrap `doc_text` in clear delimiters and instruct the model to treat it strictly as reference data, never as instructions (prompt-injection hardening).
  - Tell the model to set confidence to "low" and use "unknown" values when the docs don't clearly state something, rather than guessing.

## Part C — Research runner (`src/research.py`)
- `research_one(app: dict, model_name: str) -> AppResearch`:
  - fetch docs from `app["hint_url"]`, build the prompt, call `run_model_json`, validate into `AppResearch`.
  - always set `app_name`, `category`, `researched_by` from known inputs (don't trust the LLM for these).
  - if fetch is empty or JSON invalid, return an AppResearch with unknown/low-confidence defaults and evidence_url set to the hint_url.
- `research_all(apps: list[dict], model_name: str) -> list[AppResearch]`:
  - loop over apps, call `research_one`, print a one-line progress log per app (index, name, auth_method, confidence).
- `save_results(results: list[AppResearch], path: str)`: write to JSON (list of dicts).

## Part D — Entry script (`src/run_research.py`)
- Runnable: `python src/run_research.py --model qwen2.5:7b`
- Loads apps from `data/apps.csv`, runs `research_all`, saves to `results/research_<model>.json`.
- Use argparse for `--model` (default `qwen2.5:7b`) and `--input` (default `data/apps.csv`).

## Conventions
- Reuse spec-1 modules; do not duplicate model or schema logic.
- Each file starts with a one-line purpose comment.
- Defensive throughout: no single app failure stops the run.

## Done when
- `python src/run_research.py --model qwen2.5:7b` researches the 5 CRM apps and writes `results/research_qwen2.5:7b.json` with 5 validated rows.
- Progress prints per app; a deliberately broken URL yields an unknown/low-confidence row instead of a crash.