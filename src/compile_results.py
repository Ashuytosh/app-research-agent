# Merges both model result files against ground truth into site/data.json and bakes it into site/index.html.
import csv
import json
import re
from urllib.parse import urlparse

from input_loader import load_apps
from retrieve_all import cache_path

GEMINI_MODEL = "gemini-3.6-flash"
QWEN_MODEL = "qwen2.5:7b"
MODELS = [GEMINI_MODEL, QWEN_MODEL]

RESULTS_PATHS = {
    GEMINI_MODEL: "results/research_gemini-3.6-flash.json",
    QWEN_MODEL: "results/research_qwen2.5-7b.json",
}


def normalize_auth(raw: str) -> str:
    s = (raw or "").lower()
    if not s or s == "unknown":
        return "unknown"
    if "oauth" in s:
        return "oauth2"
    if "api key" in s or "apikey" in s:
        return "api-key"
    if "key-pair" in s or "key pair" in s:
        return "key-pair"
    if "token" in s:
        return "token"
    if "basic" in s:
        return "basic"
    return "other"


def auth_buckets(raw: str) -> set[str]:
    s = (raw or "").lower()
    if not s or s == "unknown":
        return {"unknown"}
    buckets = set()
    if "oauth" in s:
        buckets.add("oauth2")
    if "api key" in s or "apikey" in s:
        buckets.add("api-key")
    if "key-pair" in s or "key pair" in s:
        buckets.add("key-pair")
    if "token" in s:
        buckets.add("token")
    if "basic" in s:
        buckets.add("basic")
    return buckets or {"other"}


def base_domain(url: str) -> str:
    if not url:
        return ""
    netloc = urlparse(url if "://" in url else f"//{url}").netloc.lower()
    netloc = netloc.removeprefix("www.")
    parts = netloc.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else netloc


def load_results(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    return {r["app_name"]: r for r in rows}


def load_ground_truth() -> list[dict]:
    with open("data/ground_truth.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_cache_content_lengths(apps: list[dict]) -> dict[str, int]:
    lengths = {}
    for app in apps:
        try:
            with open(cache_path(app["name"]), encoding="utf-8") as f:
                entry = json.load(f)
            lengths[app["name"]] = len(entry.get("content", ""))
        except FileNotFoundError:
            lengths[app["name"]] = 0
    return lengths


def reconcile_row(app: dict, gemini_row: dict, qwen_row: dict, is_failed: bool) -> dict:
    fields = ["auth_method", "access_type", "api_surface", "has_mcp", "buildability", "main_blocker", "evidence_url", "mcp_evidence_url"]
    merged = {}
    qwen_confident = qwen_row.get("confidence") in ("high", "medium")

    for field in fields:
        g_val = gemini_row.get(field)
        q_val = qwen_row.get(field)
        g_is_empty = g_val in (None, "", "unknown", False)
        if not g_is_empty:
            merged[field] = g_val
        elif qwen_confident and q_val not in (None, "", "unknown", False):
            merged[field] = q_val
        else:
            merged[field] = g_val

    hint_domain = base_domain(app["hint_url"])
    mcp_domain = base_domain(merged.get("mcp_evidence_url", ""))
    if not merged.get("has_mcp"):
        mcp_type = "none"
    elif mcp_domain and mcp_domain == hint_domain:
        mcp_type = "official"
    else:
        mcp_type = "community"

    if is_failed:
        # Neither model's guess is trustworthy when retrieval itself failed — never surface a confident answer.
        merged["auth_method"] = "unknown"
        merged["access_type"] = "unknown"
        merged["buildability"] = "unknown"
        agreement = "retrieval-failed"
    else:
        keys = ["auth_method", "access_type", "buildability", "has_mcp"]
        agree = all(
            normalize_auth(gemini_row.get(k, "")) == normalize_auth(qwen_row.get(k, ""))
            if k == "auth_method"
            else gemini_row.get(k) == qwen_row.get(k)
            for k in keys
        )
        agreement = "agree" if agree else "disagree"

    return {
        "app_name": app["name"],
        "category": app["category"],
        "auth_method_raw": merged["auth_method"] or "unknown",
        "auth_method_bucket": normalize_auth(merged["auth_method"]),
        "access_type": merged["access_type"] or "unknown",
        "api_surface": merged["api_surface"] or "unknown",
        "has_mcp": bool(merged["has_mcp"]),
        "mcp_type": mcp_type,
        "buildability": merged["buildability"] or "unknown",
        "main_blocker": merged["main_blocker"] or "",
        "evidence_url": merged["evidence_url"] or app["hint_url"],
        "mcp_evidence_url": merged["mcp_evidence_url"] or "",
        "agreement": agreement,
    }


def build_rows(apps: list[dict], results: dict[str, dict], ground_truth_failed: set[str], content_lengths: dict[str, int]) -> list[dict]:
    rows = []
    for app in apps:
        name = app["name"]
        gemini_row = results[GEMINI_MODEL].get(name, {})
        qwen_row = results[QWEN_MODEL].get(name, {})
        is_failed = name in ground_truth_failed or content_lengths.get(name, 0) == 0
        rows.append(reconcile_row(app, gemini_row, qwen_row, is_failed))
    return rows


def compute_patterns(rows: list[dict]) -> dict:
    auth_counts: dict[str, int] = {}
    access_counts = {"self-serve": 0, "gated": 0, "unknown": 0}
    access_by_category: dict[str, dict[str, int]] = {}
    buildability_counts = {"buildable-now": 0, "needs-outreach": 0, "blocked": 0, "unknown": 0}
    mcp_counts = {"official": 0, "community": 0, "none": 0}

    for r in rows:
        auth_counts[r["auth_method_bucket"]] = auth_counts.get(r["auth_method_bucket"], 0) + 1
        access_counts[r["access_type"]] = access_counts.get(r["access_type"], 0) + 1
        cat_bucket = access_by_category.setdefault(r["category"], {"self-serve": 0, "gated": 0, "unknown": 0})
        cat_bucket[r["access_type"]] = cat_bucket.get(r["access_type"], 0) + 1
        buildability_counts[r["buildability"]] = buildability_counts.get(r["buildability"], 0) + 1
        mcp_counts[r["mcp_type"]] += 1

    return {
        "auth_method": auth_counts,
        "access_type": access_counts,
        "access_type_by_category": access_by_category,
        "buildability": buildability_counts,
        "mcp": mcp_counts,
    }


def compute_headline(rows: list[dict], patterns: dict, retrieval_coverage: dict, abstention: dict) -> dict:
    total_auth = sum(patterns["auth_method"].values())
    return {
        "buildable_now": patterns["buildability"]["buildable-now"],
        "needs_outreach": patterns["buildability"]["needs-outreach"],
        "blocked": patterns["buildability"]["blocked"],
        "unknown_buildability": patterns["buildability"]["unknown"],
        "auth_oauth2_pct": patterns["auth_method"].get("oauth2", 0) / total_auth * 100 if total_auth else 0,
        "auth_apikey_pct": patterns["auth_method"].get("api-key", 0) / total_auth * 100 if total_auth else 0,
        "abstention": {
            "sample_size": abstention["sample_size"],
            "gemini_full_abstain": abstention["per_model"][GEMINI_MODEL]["full_abstain"],
            "qwen_full_abstain": abstention["per_model"][QWEN_MODEL]["full_abstain"],
        },
    }


def field_matches(field: str, model_val, truth_val) -> bool:
    if field == "auth_method":
        return normalize_auth(truth_val) in auth_buckets(model_val)
    if field == "has_mcp":
        truth_has_mcp = truth_val != "none"
        return bool(model_val) == truth_has_mcp
    return str(model_val).strip().lower() == str(truth_val).strip().lower()


def compute_accuracy(ground_truth: list[dict], results: dict[str, dict]) -> dict:
    good_rows = [g for g in ground_truth if g["source_quality"] in ("good", "weak-source")]
    failed_rows = [g for g in ground_truth if g["source_quality"] == "retrieval-failed"]

    field_map = {"auth_method": "true_auth", "access_type": "true_access", "buildability": "true_buildability", "has_mcp": "true_mcp_type"}
    per_field = {}
    auth_diagnostics = {}
    for model in MODELS:
        per_field[model] = {}
        for field, truth_col in field_map.items():
            correct = 0
            field_diag = []
            for g in good_rows:
                model_row = results[model].get(g["app_name"], {})
                predicted = model_row.get(field)
                is_match = field_matches(field, predicted, g[truth_col])
                if is_match:
                    correct += 1
                if field == "auth_method":
                    field_diag.append((g["app_name"], predicted, g[truth_col], is_match))
            per_field[model][field] = {"correct": correct, "total": len(good_rows)}
            if field == "auth_method":
                auth_diagnostics[model] = field_diag

    abstain_fields = ["auth_method", "access_type", "buildability"]
    per_model_abstention = {}
    per_app_breakdown = {}
    for model in MODELS:
        full_abstain = 0
        hallucinated = 0
        apps_detail = []
        for g in failed_rows:
            model_row = results[model].get(g["app_name"], {})
            is_full_abstain = all(str(model_row.get(f, "unknown")).strip().lower() == "unknown" for f in abstain_fields)
            if is_full_abstain:
                full_abstain += 1
                classification = "full-abstain"
            else:
                hallucinated += 1
                classification = "hallucinated"
            apps_detail.append({
                "app_name": g["app_name"],
                "auth_method": model_row.get("auth_method", "unknown"),
                "access_type": model_row.get("access_type", "unknown"),
                "buildability": model_row.get("buildability", "unknown"),
                "classification": classification,
            })
        per_model_abstention[model] = {"full_abstain": full_abstain, "hallucinated": hallucinated, "apps": apps_detail}

    return {
        "good_sample_size": len(good_rows),
        "per_field": per_field,
        "abstention_sample_size": len(failed_rows),
        "abstention": per_model_abstention,
        "_abstention_helper": {"sample_size": len(failed_rows), "per_model": per_model_abstention},
        "_auth_diagnostics": auth_diagnostics,
    }


def compute_retrieval_coverage(apps: list[dict], content_lengths: dict[str, int], ground_truth: list[dict]) -> dict:
    empty_apps = [name for name, length in content_lengths.items() if length == 0]
    failed_rows = [g for g in ground_truth if g["source_quality"] == "retrieval-failed"]
    return {
        "total": len(apps),
        "empty_content": len(empty_apps),
        "empty_content_apps": empty_apps,
        "sample_size": len(ground_truth),
        "sample_failed_total": len(failed_rows),
        "sample_failed_apps": [{"app_name": g["app_name"], "note": g["notes"]} for g in failed_rows],
    }


def print_auth_diagnostics(auth_diagnostics: dict) -> None:
    print("\nAuth match/miss detail (good-retrieval sample):")
    for model, rows in auth_diagnostics.items():
        print(f"  {model}:")
        for app_name, predicted, truth, is_match in rows:
            status = "MATCH" if is_match else "MISS"
            print(f"    [{status}] {app_name}: predicted={predicted!r} truth={truth!r}")


def compile_data() -> dict:
    apps = load_apps("data/apps.csv")
    results = {model: load_results(RESULTS_PATHS[model]) for model in MODELS}
    ground_truth = load_ground_truth()
    ground_truth_failed = {g["app_name"] for g in ground_truth if g["source_quality"] == "retrieval-failed"}
    content_lengths = load_cache_content_lengths(apps)

    rows = build_rows(apps, results, ground_truth_failed, content_lengths)
    patterns = compute_patterns(rows)
    retrieval_coverage = compute_retrieval_coverage(apps, content_lengths, ground_truth)
    accuracy = compute_accuracy(ground_truth, results)
    headline = compute_headline(rows, patterns, retrieval_coverage, accuracy["_abstention_helper"])
    del accuracy["_abstention_helper"]
    print_auth_diagnostics(accuracy.pop("_auth_diagnostics"))

    return {
        "meta": {
            "title": "App Toolkit Research Agent — 100 apps",
            "subtitle": "A general research agent that reads a list of apps and answers: how do you authenticate, is it self-serve, what's the API surface, is there an MCP server, and can you build on it today.",
            "provenance": "Built with a Firecrawl retrieval + local/Gemini extraction pipeline; verified on a 20-app hand-checked sample.",
            "repo_url": "https://github.com/Ashuytosh/app-research-agent",
            "total_apps": len(apps),
            "models": MODELS,
        },
        "rows": rows,
        "patterns": patterns,
        "headline": headline,
        "accuracy": accuracy,
        "retrieval_coverage": retrieval_coverage,
    }


def inject_into_html(data: dict, html_path: str = "site/index.html") -> None:
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    payload = f"const RESEARCH_DATA = {json.dumps(data, indent=2)};"
    pattern = re.compile(r"/\*__DATA_START__\*/.*?/\*__DATA_END__\*/", re.DOTALL)
    replacement = f"/*__DATA_START__*/\n{payload}\n/*__DATA_END__*/"
    new_html = pattern.sub(lambda _match: replacement, html, count=1)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_html)


def print_summary(data: dict) -> None:
    h = data["headline"]
    rc = data["retrieval_coverage"]
    print(f"Total apps: {data['meta']['total_apps']}")
    print(f"Buildable now: {h['buildable_now']}  Needs outreach: {h['needs_outreach']}  Blocked: {h['blocked']}  Unknown: {h['unknown_buildability']}")
    print(f"Auth: OAuth2 {h['auth_oauth2_pct']:.1f}%  API key {h['auth_apikey_pct']:.1f}%")
    print(f"Retrieval coverage: {rc['total'] - rc['empty_content']}/{rc['total']} non-empty content ({rc['empty_content']} empty: {rc['empty_content_apps']})")
    print(f"Sample: {rc['sample_failed_total']}/{rc['sample_size']} hand-checked apps had failed retrieval")
    print("Abstention on failed-retrieval sample:")
    for model in MODELS:
        a = data["accuracy"]["abstention"][model]
        print(f"  {model}: full-abstain {a['full_abstain']}/{data['accuracy']['abstention_sample_size']}, hallucinated {a['hallucinated']}/{data['accuracy']['abstention_sample_size']}")
    print("Per-field accuracy (good-retrieval sample):")
    for model in MODELS:
        fields = data["accuracy"]["per_field"][model]
        parts = ", ".join(f"{f}={s['correct']}/{s['total']}" for f, s in fields.items())
        print(f"  {model}: {parts}")


if __name__ == "__main__":
    data = compile_data()
    with open("site/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    inject_into_html(data)
    print_summary(data)
    print("\nWrote site/data.json and updated site/index.html")
