# App Research Agent

## What this is
A take-home assignment for Composio's AI Product Ops Intern role. Build a general research agent that, given a list of apps, researches each one and captures: category + one-liner, auth method, self-serve vs gated, API surface + any MCP, buildability verdict + main blocker, and an evidence URL. Then find patterns across the whole set. Deliverable: one self-contained HTML page (deployed to Vercel) plus this repo with a README.

## Hard rules
- The agent must be GENERAL: it reads apps from an input file (data/apps.csv or data/apps.json), never hardcoded. Swap the file, re-run, works on any list.
- Free tools only. LLM brain = local Ollama (qwen2.5:7b primary) + Gemini API as reference/evaluator.
- Run Ollama models ONE AT A TIME (8GB VRAM). Finish all apps on one model, then swap.
- Gemini key lives in .env only. Never commit it. Never put it in the HTML page.
- Accuracy scoreboard = a hand-made ground-truth file for ~20 sampled apps. The evaluator LLM helps improve answers but does NOT grade itself.
- I must understand and be able to explain every part — the interview will probe it.

## How I work
- Specs-driven: phase specs go in .claude/specs/, Claude Code implements one phase at a time.
- Teach the concept briefly before implementing each phase.
- Production-quality, not college-level. Structured output, clear separation of steps.
- Use /daily-push for git after each working phase.