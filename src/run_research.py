# Entry script: extracts from cache for one model, resumable. python src/run_research.py --model qwen2.5:7b [--input data/apps.csv]
import argparse

from input_loader import load_apps
from research import research_all_cached

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--input", default="data/apps.csv")
    args = parser.parse_args()

    apps = load_apps(args.input)
    research_all_cached(apps, args.model)
