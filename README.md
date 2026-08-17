# App Research Agent

An agent that researches whether an AI toolkit can be built for a given app. It reads a list of apps, retrieves each app's real documentation, and extracts a structured verdict per app: what authentication it uses, whether a developer can self-serve credentials or has to go through a gate, its API surface, whether an MCP server exists, and whether it's buildable today. It then finds the patterns across the whole set and reports its own accuracy honestly.

This is a small, real version of the research Composio does before building a toolkit for an app — run across 100 apps instead of one.

**Live report:** _(add your Vercel URL here)_

---

## Table of contents
- [What it produces](#what-it-produces)
- [Quick start](#quick-start)
- [Results from this run](#results-from-this-run)
- [How the agent works](#how-the-agent-works)
- [Project structure](#project-structure)
- [How it was built (spec by spec)](#how-it-was-built-spec-by-spec)
- [Verification & honesty](#verification--honesty)
- [Deploy](#deploy)

---

## What it produces

For each app, one structured, schema-validated row:

| Field | Meaning |
|---|---|
| `category` + `one_liner` | What the app is, in one line |
| `auth_method` | OAuth2 / API key / token / Basic / key-pair |
| `access_type` | `self-serve` (get credentials yourself, free/trial) vs `gated` (paid plan, approval, or sales contact) |
| `api_surface` | REST / GraphQL, and rough breadth |
| `has_mcp` + `mcp_evidence_url` | Whether an MCP server exists, and where the evidence is |
| `buildability` | `buildable-now` / `needs-outreach` / `blocked` |
| `main_blocker` | The single biggest obstacle, if any |
| `evidence_url` | The real doc page every answer is grounded in |
| `confidence` | The model's self-reported confidence |

The final deliverable is a single self-contained HTML report (`site/index.html`) plus this repo.

---

## Quick start

**Prerequisites:** Python 3.11+, a virtual environment, [Ollama](https://ollama.com) with `qwen2.5:7b` pulled, and a `.env` file containing `GEMINI_API_KEY` and `FIRECRAWL_API_KEY`.

```bash
# 1. environment
python -m venv .venv
.venv\Scripts\activate            # Windows  (use source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt

# 2. run the whole agent end to end (retrieve + extract + save)
python src/pipeline.py --model gemini-3.6-flash

# 3. run a second model against the SAME cached docs — zero extra Firecrawl cost
python src/pipeline.py --model qwen2.5:7b --skip-retrieve

# 4. build the report page from the results
python src/compile_results.py
```

Open `site/index.html` in a browser to see the report.

**Run every model in one command:**
```bash
python src/pipeline.py --all-models --skip-retrieve
```

Each stage can also be run in isolation: `src/retrieve_all.py` (retrieval only), `src/run_research.py --model <name>` (extraction only).

---

## Results from this run

Researched **100 apps** across 10 categories. Key findings:

- **67 buildable**, 11 need outreach, 3 blocked; the rest returned unknown (mostly retrieval failures).  
- **Auth is concentrated:** OAuth2 (34%) and API keys (28%) cover most apps; the rest split across tokens, Basic, and key-pair.
- **Access by category is the useful signal:** developer tools, productivity, and data/scraping apps are mostly self-serve (easy wins); support/helpdesk and the ad platforms are the most gated (need outreach).
- **MCP has a hidden nuance:** of the apps with an MCP server, a large share are **community-built, not official** — a distinction a raw `has_mcp: true` hides. The report separates official / community / none.

### The headline verification finding

The agent was checked against a **20-app hand-verified sample**. The sharpest result came from the apps where retrieval failed (wrong page, empty page, or captcha wall):

| On failed-retrieval apps | Gemini 3.6 Flash | qwen2.5:7b (local) |
|---|---|---|
| Correctly answered "unknown" | **5 / 5** | **0 / 5** |
| Hallucinated a confident answer | 0 / 5 | 5 / 5 |

On good pages the two models are close (Gemini leads on the harder `buildability` field). But when the source was bad, the local model **confidently made things up every time**, while the frontier model **correctly abstained every time**. The takeaway: for grounded research, a model's calibration (knowing what it doesn't know) matters more than raw capability — and **retrieval quality, not model choice, was the real bottleneck.**

---

## How the agent works

A single command (`python src/pipeline.py`) runs four stages in order:

```
data/apps.csv                 (1) load the app list
      │
      ▼
Firecrawl search + scrape     (2) retrieve real docs, cache to disk
      │                           (the only step that spends credits)
      ▼
qwen2.5:7b / Gemini           (3) extract structured fields, grounded
      │                           strictly to the scraped page
      ▼
results/research_<model>.json (4) validate against schema + save
```

Three design decisions make it work at scale:

- **Retrieval is decoupled from extraction and cached.** Docs are scraped once into `cache/`; every model then reads from that cache. Running a second or third model costs **zero** extra Firecrawl credits — retrieval is paid for once (~300 credits for 100 apps, inside the free tier).
- **Evidence is owned by code, never the model.** The `evidence_url` is set to the page that was actually scraped, so the LLM cannot invent a source.
- **Everything is resumable.** A crash mid-run picks up where it left off; already-cached and already-extracted apps are skipped.

The agent is **general, not hardcoded**: it reads apps from a CSV. Swap the file, re-run, and it works on any app list — the 100 apps here are just today's input.

**Single-trigger orchestration:** `src/pipeline.py` is the one entry point that composes the stages. Flags: `--model` (which LLM), `--skip-retrieve` (reuse the cache, spend no credits), `--all-models` (run each model in sequence).

---

## Project structure

```
app-research-agent/
├── data/
│   ├── apps.csv              # the 100 apps (input) — name, category, hint URL
│   └── ground_truth.csv      # 20 hand-verified apps (the accuracy answer key)
├── src/
│   ├── pipeline.py           # single-trigger orchestrator (the "agent")
│   ├── input_loader.py       # reads the app list
│   ├── retriever.py          # Firecrawl search + scrape
│   ├── mcp_check.py          # dedicated MCP-server detection
│   ├── retrieve_all.py       # retrieval stage → cache/
│   ├── prompts.py            # the grounded extraction prompt
│   ├── model_runner.py       # one interface over Ollama + Gemini (adapter)
│   ├── research.py           # extraction loop → results/
│   ├── run_research.py       # extraction CLI (single model)
│   ├── run_all_models.py     # extraction for all models
│   ├── schema.py             # Pydantic schema for a research row
│   └── compile_results.py    # merges models + computes accuracy → site/
├── site/
│   ├── index.html            # the self-contained report page (deliverable)
│   └── data.json             # computed stats (also baked into the HTML)
├── cache/                    # scraped docs per app (git-ignored, regenerable)
├── results/                  # per-model output rows (git-ignored, regenerable)
├── .claude/specs/            # the build specs, one per phase
├── .env                      # API keys (never committed)
└── requirements.txt
```

`cache/` and `results/` are regenerable and git-ignored. `data/ground_truth.csv` is hand-made verified work and **is** committed.

---

## How it was built (spec by spec)

The project was built in small, verifiable phases, each specified before implementation:

1. **Schema & model runner** — the Pydantic output schema, the CSV input format, and one adapter (`run_model`) that hides the difference between Ollama and Gemini so the rest of the code is model-agnostic.
2. **Research pipeline** — the first fetch → extract → validate loop.
3. **Grounded retrieval (Firecrawl)** — *why this phase existed:* spec 2 fetched the app's hint URL directly with plain HTTP, which failed on JavaScript-heavy or bot-protected developer portals (Salesforce, HubSpot returned empty), and in one case the model **invented an evidence URL**. Spec 3 replaced direct fetching with **Firecrawl search-then-scrape** (finds a real, fetchable docs page) and made **code, not the model, own the evidence URL** — killing both the empty-page and fabricated-source problems.
4. **MCP signal & buildability logic** — `has_mcp` was being wrongly inferred from auth pages that never mention MCP, so it got its own dedicated search; and the buildability rule was rewritten so "no MCP" is never treated as a blocker.
5. **Full run: caching + multi-model** — scaled to 100 apps, split retrieval (cached once) from extraction (run per model), made both resumable.
6. **Single-trigger orchestrator** — composed the stages into one `pipeline.py` command.
7. **Compile & report** — merges the models into one best-answer table, computes accuracy against the ground-truth sample, and generates the HTML report.

A smaller local model (`gemma3:4b`) was also tested and **dropped** — it produced malformed JSON often enough to break the run and defaulted almost everything to "gated." Documenting that is itself a finding about the floor on model size for this task.

---

## Verification & honesty

Accuracy is measured against `data/ground_truth.csv` — 20 apps hand-checked against their real documentation. The compile script recomputes every number from the actual `results/*.json` files on each run, so nothing on the report is hand-typed.

Known limitations (detailed in the report's Flaws section):
- **Retrieval was the bottleneck.** ~5% of apps got a wrong or empty page — wrong-company results for obscure apps (search had nothing better), marketing pages instead of docs, and one captcha-walled site (Stripe) we chose not to bypass to stay in Firecrawl's free tier.
- **qwen over-commits; Gemini over-abstains.** The local model hallucinates on thin pages; the frontier model sometimes says "unknown" on pages that do contain an awkwardly-phrased answer.
- **MCP detection is coarse.** It flags any credible MCP server; the official-vs-community split is a domain heuristic, not a guarantee.

Next steps if continued: prefer docs-subdomains over homepages when choosing a search result, use stealth-mode scraping for captcha sites, add a reconciliation/judge pass instead of a static model-preference rule, and grow the verified sample beyond 20 apps.

---

## Deploy

`site/index.html` is one self-contained file (inline CSS/JS, data baked in) — no build step, no external requests. It renders opened directly as a local file or served by any static host.

- **Vercel:** point a new project at this repo with the root directory set to `site/`.
- **Drag-and-drop:** drag the `site/` folder onto Vercel or Netlify.

Regenerate the report's data after any new research run:

```bash
python src/compile_results.py
```

This reads `results/research_*.json` and `data/ground_truth.csv`, recomputes every stat, and rewrites `site/data.json` and the baked-in data block in `site/index.html` — safe to re-run; it never touches the page's markup or styling.