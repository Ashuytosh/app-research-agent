# Spec 5 — Full 100-App Run: Cached Retrieval + Multi-Model Extraction

## Objective
Scale from 5 apps to all 100, across three models (qwen2.5:7b, gemma3:4b, gemini-3.6-flash), without multiplying Firecrawl cost. Split the pipeline into two phases: retrieve-once (spends Firecrawl credits, cached to disk) and extract-per-model (reads cache, no Firecrawl). Both phases must be resumable so a crash never forces a full restart.

## Input
- data/apps.csv now contains all 100 apps (name, category, hint_url).

## Part A — Retrieval cache (`src/retrieve_all.py`)
- For each app in data/apps.csv:
  - Compute a safe slug from the app name (lowercase, non-alphanumeric -> "-").
  - Cache path: `cache/<slug>.json`.
  - If the cache file already exists AND has non-empty content, SKIP (resumable — no re-spend).
  - Otherwise: call `search_and_scrape(name, hint_url)` and `check_mcp(name)`, then save a JSON: `{ "app_name", "category", "hint_url", "scraped_url", "content", "has_mcp", "mcp_evidence_url" }`.
- This is the ONLY Firecrawl-spending step in the whole project.
- Add a small polite delay (e.g. 1s) between apps to respect free-tier concurrency (2).
- Log per app: index/100, name, scraped_url, content length, has_mcp.
- Print a final summary: how many cached fresh, how many skipped, how many had empty content.
- Never let one app's failure stop the loop.

## Part B — Extraction reads from cache (`src/research.py`)
- Add `research_one_cached(cache_entry: dict, model_name: str) -> AppResearch`:
  - Uses `cache_entry["content"]` as the doc text (no Firecrawl call).
  - Builds the prompt, calls run_model_json, validates into AppResearch.
  - Sets app_name, category, researched_by from the cache entry / model name.
  - Sets evidence_url = cache_entry["scraped_url"] (code-owned, never model).
  - Sets has_mcp and mcp_evidence_url from the cache entry (already decided in Part A).
  - Empty content -> unknown/low-confidence row with evidence_url = scraped_url or hint_url.
- Keep the existing spec-3/4 logic; this is a cache-fed variant of research_one.

## Part C — Per-model runner (`src/run_research.py`)
- `python src/run_research.py --model <name>`:
  - Loads all cache entries from `cache/` (in the order of data/apps.csv).
  - Output path: `results/research_<sanitized-model>.json`.
  - RESUMABLE: if the output file exists, load it, and skip apps already present (match by app_name). Only research the missing ones, then merge and save.
  - Save incrementally (write the growing results list after every app) so a crash mid-run loses nothing.
  - Add a small delay between Gemini calls (e.g. 1-2s) to stay under free-tier RPM limits; no delay needed for local Ollama.
  - Progress log per app: index/100, name, auth_method, buildability, confidence.
- Default model stays qwen2.5:7b.

## Part D — One-shot convenience (`src/run_all_models.py`)
- Runs extraction for a list of models in sequence: ["qwen2.5:7b", "gemma3:4b", "gemini-3.6-flash"].
- For Ollama models, they run one at a time (VRAM) — this script just calls them sequentially, it does NOT load two at once.
- Prints which model is running and where its output landed.

## Conventions
- Reuse retriever, mcp_check, model_runner, schema, input_loader.
- cache/ and results/ stay gitignored (already the case for results/; add cache/ to .gitignore).
- One-line purpose comment at top of each new/changed file.
- No feature that spends Firecrawl outside Part A.

## Done when
- `python src/retrieve_all.py` populates cache/ with up to 100 JSON files, logs progress, and re-running it skips everything already cached (spends ~0 new credits).
- `python src/run_research.py --model qwen2.5:7b` produces results/research_qwen2.5-7b.json with 100 rows, reading only from cache.
- Re-running the same command after a partial run resumes and does not re-research completed apps.
- Running the other two models produces their own results files, with no additional Firecrawl spend.