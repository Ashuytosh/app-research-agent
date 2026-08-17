# Core research loop: fetch docs, extract via LLM, validate into AppResearch, save results.
import json
import os
import time

from pydantic import ValidationError

from mcp_check import check_mcp
from model_runner import run_model_json
from prompts import build_research_prompt
from retriever import search_and_scrape
from retrieve_all import cache_path
from schema import AppResearch


def _fallback(app_name: str, category: str, model_name: str, evidence_url: str, mcp_result: dict) -> AppResearch:
    return AppResearch(
        app_name=app_name,
        category=category,
        researched_by=model_name,
        evidence_url=evidence_url,
        has_mcp=mcp_result["has_mcp"],
        mcp_evidence_url=mcp_result["mcp_evidence_url"],
    )


def _build_result(
    app_name: str, category: str, model_name: str, content: str, evidence_url: str, mcp_result: dict
) -> AppResearch:
    prompt = build_research_prompt(app_name, category, content)
    extracted = run_model_json(model_name, prompt)
    if not extracted:
        return _fallback(app_name, category, model_name, evidence_url, mcp_result)

    extracted.update(
        app_name=app_name,
        category=category,
        researched_by=model_name,
        evidence_url=evidence_url,
        has_mcp=mcp_result["has_mcp"],
        mcp_evidence_url=mcp_result["mcp_evidence_url"],
    )
    try:
        return AppResearch(**extracted)
    except ValidationError:
        return _fallback(app_name, category, model_name, evidence_url, mcp_result)


def research_one(app: dict, model_name: str) -> AppResearch:
    retrieved = search_and_scrape(app["name"], app["hint_url"])
    mcp_result = check_mcp(app["name"])
    category = app.get("category", "unknown")
    return _build_result(app["name"], category, model_name, retrieved["content"], retrieved["url"], mcp_result)


def research_one_cached(cache_entry: dict, model_name: str) -> AppResearch:
    mcp_result = {"has_mcp": cache_entry["has_mcp"], "mcp_evidence_url": cache_entry["mcp_evidence_url"]}
    evidence_url = cache_entry["scraped_url"] or cache_entry["hint_url"]
    return _build_result(
        cache_entry["app_name"],
        cache_entry.get("category", "unknown"),
        model_name,
        cache_entry["content"],
        evidence_url,
        mcp_result,
    )


def _load_cache_entry(app_name: str) -> dict | None:
    path = cache_path(app_name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_existing_results(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    return {row["app_name"]: row for row in rows}


def _save_result_rows(rows: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)


def research_all_cached(apps: list[dict], model_name: str) -> dict:
    safe_model_name = model_name.replace(":", "-")
    output_path = f"results/research_{safe_model_name}.json"

    existing = _load_existing_results(output_path)
    results = list(existing.values())

    for i, app in enumerate(apps, start=1):
        name = app["name"]
        if name in existing:
            print(f"[{i}/{len(apps)}] {name}: already done, skipping")
            continue

        cache_entry = _load_cache_entry(name)
        if cache_entry is None:
            print(f"[{i}/{len(apps)}] {name}: not cached, skipping (run retrieve_all.py first)")
            continue

        result = research_one_cached(cache_entry, model_name)
        results.append(result.model_dump())
        _save_result_rows(results, output_path)
        print(
            f"[{i}/{len(apps)}] {name}: auth={result.auth_method} "
            f"buildability={result.buildability} confidence={result.confidence}"
        )

        if model_name.startswith("gemini"):
            time.sleep(1.5)

    by_confidence = {"high": 0, "medium": 0, "low": 0}
    by_buildability = {"buildable-now": 0, "needs-outreach": 0, "blocked": 0, "unknown": 0}
    for row in results:
        by_confidence[row["confidence"]] = by_confidence.get(row["confidence"], 0) + 1
        by_buildability[row["buildability"]] = by_buildability.get(row["buildability"], 0) + 1

    return {
        "output_path": output_path,
        "rows_written": len(results),
        "by_confidence": by_confidence,
        "by_buildability": by_buildability,
    }


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
