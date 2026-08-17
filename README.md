# App Research Agent

A research agent that reads a list of apps from `data/apps.csv`, researches each one, and produces a structured JSON row per app: category + one-liner, auth method, self-serve vs gated, API surface + MCP presence, buildability verdict + main blocker, and a real evidence URL.

## How to run

Run the full pipeline (load apps, retrieve + cache docs via Firecrawl, extract with an LLM, save results):

```
python src/pipeline.py --model gemini-3.6-flash
```

Re-run extraction with a different model against the same cached docs, at zero additional Firecrawl cost:

```
python src/pipeline.py --model qwen2.5:7b --skip-retrieve
```

Run every model in sequence in one go:

```
python src/pipeline.py --all-models --skip-retrieve
```

Each stage also has its own standalone script if you want to run it in isolation: `src/retrieve_all.py` (retrieval only), `src/run_research.py --model <name>` (extraction only), `src/run_all_models.py` (extraction for all models).

### Where things live
- `cache/` — one JSON file per app with the scraped docs content and MCP check result. Populated by the retrieval stage; re-running it skips apps already cached.
- `results/` — one JSON file per model (`research_<model>.json`), each a resumable list of rows.
- `.env` — holds `GEMINI_API_KEY` and `FIRECRAWL_API_KEY`. Never committed.

## What each stage does
The pipeline loads the app list, then retrieves and caches real documentation pages via Firecrawl search + scrape (the only step that spends Firecrawl credits), checks for an official MCP server per app, extracts structured fields with a local Ollama model or Gemini, validates the output against a schema, and saves it. A human is still needed for two things this pipeline doesn't automate: building the final HTML presentation page from the results, and hand-verifying a sampled subset of rows against ground truth for the accuracy scoreboard.
