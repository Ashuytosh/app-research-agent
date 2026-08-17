# Entry script: spends Firecrawl credits once per app, caching results to disk. python src/retrieve_all.py [--input data/apps.csv]
import argparse
import json
import os
import re
import time

from input_loader import load_apps
from mcp_check import check_mcp
from retriever import search_and_scrape

CACHE_DIR = "cache"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def cache_path(app_name: str) -> str:
    return os.path.join(CACHE_DIR, f"{slugify(app_name)}.json")


def _is_cached(app_name: str) -> bool:
    path = cache_path(app_name)
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    return bool(entry.get("content"))


def retrieve_one(app: dict) -> dict:
    retrieved = search_and_scrape(app["name"], app["hint_url"])
    mcp_result = check_mcp(app["name"])
    return {
        "app_name": app["name"],
        "category": app.get("category", "unknown"),
        "hint_url": app["hint_url"],
        "scraped_url": retrieved["url"],
        "content": retrieved["content"],
        "has_mcp": mcp_result["has_mcp"],
        "mcp_evidence_url": mcp_result["mcp_evidence_url"],
    }


def retrieve_all(apps: list[dict]) -> dict:
    os.makedirs(CACHE_DIR, exist_ok=True)
    fresh, skipped, empty = 0, 0, 0

    for i, app in enumerate(apps, start=1):
        name = app["name"]
        if _is_cached(name):
            print(f"[{i}/{len(apps)}] {name}: cached, skipping")
            skipped += 1
            continue

        try:
            entry = retrieve_one(app)
        except Exception as exc:
            print(f"[{i}/{len(apps)}] {name}: FAILED ({exc}), will retry on next run")
            continue

        with open(cache_path(name), "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2)

        if not entry["content"]:
            empty += 1
        fresh += 1
        print(
            f"[{i}/{len(apps)}] {name}: scraped_url={entry['scraped_url']} "
            f"content_len={len(entry['content'])} has_mcp={entry['has_mcp']}"
        )
        time.sleep(1)

    print(f"\nDone: {fresh} freshly cached, {skipped} skipped (already cached), {empty} had empty content.")
    return {"fresh": fresh, "skipped": skipped, "empty": empty}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/apps.csv")
    args = parser.parse_args()

    retrieve_all(load_apps(args.input))
