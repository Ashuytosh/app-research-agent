# Reads the app input file (CSV) into a list of dicts. Apps are never hardcoded — swap the file, re-run.
import csv


def load_apps(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
