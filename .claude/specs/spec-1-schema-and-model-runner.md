# Spec 1 — Schema, Input File, and Model Runner

## Objective
Build the foundation of the research agent: a strict data schema for the research fields, the input-file format the agent reads apps from, and a unified model runner that calls both local Ollama models and Gemini through one interface. This spec is the spine; research and verification logic come in later specs.

## Part A — Research schema (`src/schema.py`)
Use Pydantic v2. Define an `AppResearch` model with these fields, each with a short docstring and a safe default so partial results never crash:

- `app_name: str`
- `category: str` — one of the 10 app categories
- `one_liner: str` — one line on what the app does
- `auth_method: str` — e.g. "OAuth2", "API key", "Basic", "token", "other"
- `access_type: str` — one of: "self-serve", "gated", "unknown"
- `api_surface: str` — REST / GraphQL / none, plus rough breadth
- `has_mcp: bool` — whether a known official MCP server exists
- `buildability: str` — one of: "buildable-now", "needs-outreach", "blocked", "unknown"
- `main_blocker: str` — biggest blocker if not buildable now; empty if none
- `evidence_url: str` — docs/article URL supporting the answer
- `confidence: str` — model self-confidence: "high" / "medium" / "low"
- `researched_by: str` — model that produced the row (e.g. "qwen2.5:7b")

## Part B — Input file (`data/apps.csv` + `src/input_loader.py`)
- `data/apps.csv` with columns: `name`, `category`, `hint_url`. Seed with the first 5 CRM apps: Salesforce, HubSpot, Pipedrive, Attio, Twenty.
- `src/input_loader.py` with `load_apps(path: str) -> list[dict]` that reads the CSV into a list of app dicts. Apps are always read from this file, never hardcoded, so the agent works on any list.

## Part C — Model runner (`src/model_runner.py`)
A single interface so the rest of the agent is model-agnostic (adapter pattern):
- `run_model(model_name: str, prompt: str) -> str`:
  - name starting with "gemini" → call Gemini via `google-genai` (model `gemini-3.6-flash`), key from `.env` via python-dotenv.
  - otherwise → call it as an Ollama model via the `ollama` package.
  - returns raw text.
- `run_model_json(model_name: str, prompt: str) -> dict`: calls `run_model`, strips code fences, safely parses JSON, returns `{}` on failure instead of crashing.
- `load_dotenv()` at module import. The runner calls one model at a time; it never loads two Ollama models simultaneously (8GB VRAM). Model-swapping is the caller's job.

## Part D — Smoke test (`src/smoke_test.py`)
Runnable via `python src/smoke_test.py`:
1. Load and print the 5 apps from `data/apps.csv`.
2. `run_model("qwen2.5:7b", "Reply with exactly: ollama works")` and print.
3. `run_model("gemini-3.6-flash", "Reply with exactly: gemini works")` and print.

## Conventions
- Pydantic v2 syntax. Each file starts with a one-line comment describing its purpose.
- No scraping, research, or verification logic in this spec — foundation only.
- Simple, readable, production-quality.

## Done when
- `python src/smoke_test.py` prints the 5 apps, "ollama works", and "gemini works".
- `src/schema.py`, `src/input_loader.py`, `src/model_runner.py` import cleanly.