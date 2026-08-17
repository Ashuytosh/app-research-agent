# Core research loop: fetch docs, extract via LLM, validate into AppResearch, save results.
import json
import os

from pydantic import ValidationError

from fetcher import fetch_docs
from model_runner import run_model_json
from prompts import build_research_prompt
from schema import AppResearch


def _fallback(app: dict, model_name: str) -> AppResearch:
    return AppResearch(
        app_name=app["name"],
        category=app.get("category", "unknown"),
        researched_by=model_name,
        evidence_url=app.get("hint_url", ""),
    )


def research_one(app: dict, model_name: str) -> AppResearch:
    doc_text = fetch_docs(app["hint_url"])
    if not doc_text:
        return _fallback(app, model_name)

    prompt = build_research_prompt(app["name"], app.get("category", "unknown"), doc_text)
    extracted = run_model_json(model_name, prompt)
    if not extracted:
        return _fallback(app, model_name)

    extracted.update(app_name=app["name"], category=app.get("category", "unknown"), researched_by=model_name)
    try:
        return AppResearch(**extracted)
    except ValidationError:
        return _fallback(app, model_name)


def research_all(apps: list[dict], model_name: str) -> list[AppResearch]:
    results = []
    for i, app in enumerate(apps, start=1):
        result = research_one(app, model_name)
        print(f"[{i}/{len(apps)}] {app['name']}: auth={result.auth_method} confidence={result.confidence}")
        results.append(result)
    return results


def save_results(results: list[AppResearch], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in results], f, indent=2)
