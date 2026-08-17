# Verifies input loading, Ollama, and Gemini all work end to end. Run via: python src/smoke_test.py
from input_loader import load_apps
from model_runner import run_model

if __name__ == "__main__":
    apps = load_apps("data/apps.csv")
    print(apps)

    print(run_model("qwen2.5:7b", "Reply with exactly: ollama works"))

    print(run_model("gemini-3.6-flash", "Reply with exactly: gemini works"))
