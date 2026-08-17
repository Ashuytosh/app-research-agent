# Spec 6 — Single-Trigger Pipeline Orchestrator

## Objective
Wrap the existing stages into ONE runnable pipeline so a single command runs the whole agent end to end: load apps -> retrieve+cache (Firecrawl) -> MCP check -> LLM extraction -> validate -> store results. The HTML page is produced separately (manual, presentation only). This does not rewrite the stages; it composes the functions that already exist.

## Precondition
The stage logic already exists and works: input_loader, retriever (search_and_scrape), mcp_check, research (research_one_cached / research_all), model_runner, schema. Reuse them as imported functions. Do NOT duplicate their logic.

## Part A — Expose each stage as a callable function
Ensure each stage file exposes a clean function (refactor only if it's currently script-only):
- input_loader.load_apps(path) -> list[dict]
- retrieve_all.retrieve_all(apps) -> writes/updates cache/, returns summary dict (fresh, skipped, empty)
- research.research_all_cached(model_name) -> reads cache/, returns list[AppResearch], saves results/research_<model>.json
Keep their existing CLI entry points working too.

## Part B — The orchestrator (`src/pipeline.py`)
A single entry point that runs the full flow:
- CLI: `python src/pipeline.py --model gemini-3.6-flash --input data/apps.csv`
- Steps, in order, with a clear printed banner before each:
  1. load apps from --input
  2. retrieve_all(apps)  -> populate/refresh cache (skips already-cached; this is the only Firecrawl spend)
  3. research_all_cached(model)  -> extraction over the cache, save results/research_<model>.json
  4. print a final summary: total apps, cached fresh/skipped/empty, rows written, output path, and a count of rows by confidence (high/medium/low) and by buildability.
- Flags:
  - --model (default gemini-3.6-flash)
  - --input (default data/apps.csv)
  - --skip-retrieve (bool): if set, skip stage 2 and go straight to extraction from existing cache (for re-running models cheaply)
- Defensive: any single app failure is logged and skipped, never crashes the pipeline (reuse existing per-app try/except).
- Never spends Firecrawl outside stage 2; --skip-retrieve makes model re-runs cost zero credits.

## Part C — Optional: run multiple models in one go (`src/pipeline.py --all-models`)
- If --all-models is passed, run stage 2 once, then stage 3 sequentially for a fixed list [gemini-3.6-flash, qwen2.5:7b], each saving its own results file. (gemma excluded — documented as unreliable.)
- Ollama models run one at a time (VRAM); this just calls them in sequence.

## Part D — README section
Add a short "How to run" block to README.md:
- one-liner to run the full pipeline
- how to re-run a model without re-spending credits (--skip-retrieve)
- where outputs land (results/), where cache lives, that .env holds keys
- one paragraph: what each stage does and where a human is still needed (the HTML page + the sample verification)

## Conventions
- Compose existing functions; no logic duplication.
- Clear stage banners in output so a viewer can watch the pipeline flow.
- One-line purpose comment at top of pipeline.py.

## Done when
- `python src/pipeline.py --model gemini-3.6-flash` runs load -> retrieve(cached) -> extract -> save with visible stage banners and a final summary, no manual steps.
- `python src/pipeline.py --model qwen2.5:7b --skip-retrieve` re-runs extraction from cache with zero Firecrawl spend.
- Existing per-stage scripts still work independently.