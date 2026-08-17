# Spec 7 — Compile Results + Single Self-Contained HTML Page

## Objective
Produce the final deliverable: (1) a compile script that reads both model result files and data/ground_truth.csv, computes accuracy, and merges the models into one best-answer table; (2) a single self-contained HTML page a reviewer understands in ~2 minutes — patterns first, then the table, model comparison, and honest verification. Presentation quality is the point.

## Part A — Compile script (`src/compile_results.py`)
Reads:
- results/research_gemini-3.6-flash.json
- results/research_qwen2.5-7b.json
- data/ground_truth.csv
Produces `site/data.json` containing everything the page needs (so the HTML has zero external calls). It must compute, from the actual files (not hardcoded):

1. **Merged best-answer table (100 rows)**: for each app, a reconciled row. Rule: prefer Gemini's value; where Gemini is "unknown" but qwen is confident, fall back to qwen and mark it. Include a per-row `agreement` flag: "agree" (both same), "disagree" (differ), or "retrieval-failed" (evidence content was empty/wrong — detect via the known failed set or empty content).
2. **Pattern stats across the merged 100**: count by auth_method; count by access_type (self-serve vs gated vs unknown) overall and per category; count by buildability; count of official vs community vs no MCP (use mcp_evidence_url domain heuristic: official if evidence domain matches the app's own domain, else community, else none).
3. **Accuracy vs ground_truth.csv**: split into (a) the good-retrieval sampled apps → per-field accuracy (auth, access_type, buildability, has_mcp) for BOTH models; (b) the retrieval-failed sampled apps → abstention rate (did the model correctly return unknown vs hallucinate) for BOTH models. Output the exact counts and percentages.
4. **Retrieval coverage**: how many of 100 apps had usable content vs empty/failed.

Print a summary to console too. This script must be re-runnable and deterministic.

## Part B — The HTML page (`site/index.html`)
ONE self-contained file. Inline CSS in a <style> tag, inline JS in a <script> tag, and the data either fetched from site/data.json (same folder) OR — safer for a static host — baked in: have compile_results.py write data.json AND also inject it into the HTML as a JS const so the page works even when opened as a bare file. Prefer baking it in.

No external libraries, no CDN, no build step. Must open and render offline.

Read /mnt/skills/public/frontend-design/SKILL.md before writing the HTML for styling quality. The page must look clean and professional, not templated.

### Page structure (top to bottom), each section skimmable in seconds:

1. **Header**: title ("App Toolkit Research Agent — 100 apps"), one-line subtitle explaining what this is. Small line: "Built with a Firecrawl retrieval + local/Gemini extraction pipeline; verified on a 20-app hand-checked sample."

2. **The headline findings** (the most important block — 3-4 big stat cards a reviewer reads first):
   - "X of 100 apps buildable now" (green)
   - "Y need outreach, Z blocked"
   - "Auth: OAuth2 and API keys dominate" with the split
   - The killer stat: "On failed-retrieval apps, the local model hallucinated 100% of the time; the frontier model abstained 100% of the time." Make this visually prominent.

3. **Patterns** (charts done in pure HTML/CSS bars — NO chart library):
   - Auth method distribution (horizontal bars)
   - Self-serve vs gated, broken down by the 10 categories (so the reviewer sees "dev tools = easy wins, ads = gated")
   - MCP: official vs community vs none (this is a nuance most miss — highlight it)
   - A one-sentence plain-English takeaway under each chart.

4. **The results matrix** (100 rows): compact, skimmable table — app, category, auth, access (color chip: green self-serve / amber gated / grey unknown), buildability (color chip), MCP (official/community/none badge), and a link to the evidence URL. Make it filterable by category and buildability with plain JS (dropdowns), and sortable. Rows flagged "retrieval-failed" visually muted.

5. **Model comparison + accuracy** (the verification section — honesty is scored here):
   - The accuracy table (auth/access/buildability/mcp %, qwen vs Gemini, on the good-retrieval sample).
   - The abstention table (0/5 vs 5/5).
   - 3-4 sentences plain English: what each model is good/bad at, why Gemini's honesty matters, that gemma3:4b was tested and dropped as unreliable (one line).

6. **Flaws & improvements** (honest, concise — bullet style, not essay):
   - Retrieval was the bottleneck: ~5% of apps got wrong/empty pages (wrong-company search results for obscure apps, marketing pages instead of docs, Stripe's captcha wall we chose not to pay 5x credits to bypass). Name the real causes.
   - qwen's paywall-hallucination bias; Gemini's over-abstention on thin pages.
   - MCP detection finds any MCP incl. community ones — official-vs-community is a known limitation we partially flag.
   - Improvements if continued: docs-subdomain preference over homepages, stealth-mode scrape for captcha sites, a reconciliation/judge pass, larger verified sample.
   Keep each point to 1-2 lines. Honest but not self-flagellating.

7. **How it works** (tiny diagram or 4-step strip): apps.csv -> Firecrawl retrieve+cache -> LLM extract -> reconcile+verify. One line on "where a human was needed" (the 20-app hand verification).

8. **Footer**: link to the GitHub repo, note that everything is reproducible via `python src/pipeline.py`.

### Design requirements
- Clean, modern, professional. Generous whitespace, clear type hierarchy, a restrained accent color, color chips for status.
- Fully responsive (reviewer may open on a laptop).
- The four headline stats and the accuracy story must be understandable WITHOUT reading any paragraph — visual first.
- No emojis. No filler text. Plain English everywhere — a non-technical reader should grasp the findings; a technical one should find the depth.

## Part C — Deploy notes in README
Add a short "Deploy" section: the page is site/index.html, self-contained; deploy by pointing Vercel at the repo (root = site/) or drag-drop the folder. Include the one-liner to regenerate data: `python src/compile_results.py`.

## Conventions
- compile_results.py reuses schema/paths; deterministic; prints a summary.
- The HTML is the ONLY presentation artifact; all numbers come from compile_results.py, never hardcoded in HTML.
- Read frontend-design SKILL.md before writing HTML.

## Done when
- `python src/compile_results.py` writes site/data.json (and injects data into site/index.html) with real computed stats.
- Opening site/index.html shows: headline stats, pattern charts, filterable 100-row table, accuracy tables, honest flaws section — all populated from real data, rendering offline.
- The four headline findings and the 0/5-vs-5/5 accuracy story are graspable in under 2 minutes with no narration.