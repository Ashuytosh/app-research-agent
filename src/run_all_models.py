# One-shot convenience: runs extraction for all three models in sequence. python src/run_all_models.py [--input data/apps.csv]
import argparse
import subprocess
import sys

MODELS = ["qwen2.5:7b", "gemma3:4b", "gemini-3.6-flash"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/apps.csv")
    args = parser.parse_args()

    for model in MODELS:
        safe_model_name = model.replace(":", "-")
        print(f"\n=== Running {model} -> results/research_{safe_model_name}.json ===")
        subprocess.run(
            [sys.executable, "src/run_research.py", "--model", model, "--input", args.input],
            check=True,
        )
