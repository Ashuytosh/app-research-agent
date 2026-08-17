# Unified interface for calling either local Ollama models or Gemini, so the rest of the agent is model-agnostic.
import json
import os

import ollama
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Ollama models run ONE AT A TIME (8GB VRAM budget). Swapping models between
# batches of apps is the caller's responsibility — this module never loads
# two Ollama models concurrently.


def run_model(model_name: str, prompt: str) -> str:
    if model_name.startswith("gemini"):
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(model=model_name, contents=prompt)
        return response.text

    response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]


def run_model_json(model_name: str, prompt: str) -> dict:
    raw = run_model(model_name, prompt).strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
