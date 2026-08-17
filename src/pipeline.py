# Single-trigger orchestrator: composes load -> retrieve+cache -> extract -> save into one run.
import argparse

from input_loader import load_apps
from research import research_all_cached
from retrieve_all import retrieve_all

ALL_MODELS = ["gemini-3.6-flash", "qwen2.5:7b"]


def _banner(text: str) -> None:
    print(f"\n=== {text} ===")


def run_pipeline(input_path: str, model: str, skip_retrieve: bool, all_models: bool) -> None:
    _banner("STAGE 1: Load apps")
    apps = load_apps(input_path)
    print(f"Loaded {len(apps)} apps from {input_path}")

    retrieve_summary = None
    if skip_retrieve:
        _banner("STAGE 2: Retrieve + cache (SKIPPED via --skip-retrieve)")
    else:
        _banner("STAGE 2: Retrieve + cache (Firecrawl)")
        retrieve_summary = retrieve_all(apps)

    models = ALL_MODELS if all_models else [model]
    extraction_summaries = {}
    for m in models:
        _banner(f"STAGE 3: Extraction ({m})")
        extraction_summaries[m] = research_all_cached(apps, m)

    _banner("SUMMARY")
    print(f"Total apps: {len(apps)}")
    if retrieve_summary is not None:
        print(
            f"Retrieval: {retrieve_summary['fresh']} fresh, "
            f"{retrieve_summary['skipped']} skipped, {retrieve_summary['empty']} empty content"
        )
    else:
        print("Retrieval: skipped (--skip-retrieve)")

    for m, summary in extraction_summaries.items():
        print(f"\nModel: {m}")
        print(f"  Output: {summary['output_path']}")
        print(f"  Rows written: {summary['rows_written']}")
        print(f"  By confidence: {summary['by_confidence']}")
        print(f"  By buildability: {summary['by_buildability']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gemini-3.6-flash")
    parser.add_argument("--input", default="data/apps.csv")
    parser.add_argument("--skip-retrieve", action="store_true")
    parser.add_argument("--all-models", action="store_true")
    args = parser.parse_args()

    run_pipeline(args.input, args.model, args.skip_retrieve, args.all_models)
