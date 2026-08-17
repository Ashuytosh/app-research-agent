# Entry script: python src/run_research.py --model qwen2.5:7b --input data/apps.csv
import argparse

from input_loader import load_apps
from research import research_all, save_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--input", default="data/apps.csv")
    args = parser.parse_args()

    apps = load_apps(args.input)
    results = research_all(apps, args.model)
    safe_model_name = args.model.replace(":", "-")
    save_results(results, f"results/research_{safe_model_name}.json")
