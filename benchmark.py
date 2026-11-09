import argparse
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median

LOCAL = "Local Edge (Tier 2)"
CLOUD = "Cloud (Tier 3)"
OLLAMA_LARGE = "Ollama (Large)"


def load_results(path):
    rows = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or any(
        not isinstance(row, dict) or not isinstance(row.get("routed_to"), str)
        for row in rows
    ):
        raise ValueError(f"{path} must contain a JSON array of results with route labels.")
    return rows


def paired_results(routed, baseline):
    def index(rows, mode):
        indexed = {}
        for row in rows:
            task_id = row.get("id")
            digest = row.get("prompt_sha256")
            if row.get("mode") != mode or not isinstance(task_id, str) or not isinstance(digest, str) or task_id in indexed:
                raise ValueError(f"{mode} results need unique task IDs, prompt hashes, and the correct run mode.")
            indexed[task_id] = digest
        return indexed

    ollama = bool(routed) and routed[0].get("mode") == "ollama-routed"
    routed_mode, baseline_mode = ("ollama-routed", "ollama-large-only") if ollama else ("routed", "cloud-only")
    if not routed or index(routed, routed_mode) != index(baseline, baseline_mode):
        raise ValueError("Comparison requires nonempty runs with identical task IDs and prompts.")
    if ollama:
        models = routed[0].get("ollama_models")
        if not isinstance(models, list) or len(models) != 2 or any(
            row.get("ollama_models") != models for run in (routed, baseline) for row in run
        ):
            raise ValueError("Ollama comparison requires identical model settings across both runs.")
    return baseline_mode


def token_total(rows, key):
    values = [row.get(key) for row in rows]
    observed = [value for value in values if type(value) is int and value >= 0]
    if not observed:
        return "unavailable"
    return f"{sum(observed)} observed ({len(observed)}/{len(rows)} results with data)"


def summarize(rows):
    routes = Counter(row["routed_to"] for row in rows)
    local, cloud = routes[LOCAL], routes[CLOUD]
    large = routes[OLLAMA_LARGE]
    failed = routes["Error"] + routes["Cloud (Error)"] + routes["Ollama (Error)"]
    ollama = bool(rows) and rows[0].get("mode") in ("ollama-routed", "ollama-large-only")
    print(f"Total results: {len(rows)}")
    print(f"Handled locally: {local}")
    if ollama:
        print(f"Handled by the large Ollama model: {large}")
        print(f"Large-model attempts: {large + routes['Ollama (Error)']}")
        print(f"Answered by the small model: {local}/{len(rows)} ({100 * local / len(rows):.1f}%)")
    else:
        print(f"Handled in the cloud: {cloud}")
        rate = f"{100 * local / len(rows):.1f}%" if rows else "N/A (no results)"
        print(f"Local share of all results: {rate}")
    print(f"Failed: {failed}")
    print(f"Unrecognized route: {len(rows) - local - cloud - large - failed}")
    timings = sorted(
        row["latency_ms"] for row in rows
        if type(row.get("latency_ms")) in (int, float)
        and math.isfinite(row["latency_ms"]) and row["latency_ms"] >= 0
    )
    if timings:
        p95 = timings[math.ceil(0.95 * len(timings)) - 1]
        print(f"Latency: p50 {median(timings):.2f} ms, p95 {p95:.2f} ms ({len(timings)}/{len(rows)} results)")
    else:
        print("Latency: unavailable")
    if ollama:
        return
    print("Cloud input tokens: " + token_total(rows, "cloud_input_tokens"))
    print("Cloud output tokens: " + token_total(rows, "cloud_output_tokens"))


def main():
    parser = argparse.ArgumentParser(description="Summarize EcoRoute runs and optionally compare a matched baseline.")
    parser.add_argument("results", nargs="?", type=Path, default=Path("output/results.json"))
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    try:
        routed = load_results(args.results)
        baseline = load_results(args.baseline) if args.baseline else None
        if baseline is not None:
            baseline_mode = paired_results(routed, baseline)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Could not compare results: {exc}\n")

    print("EcoRoute results")
    summarize(routed)
    if baseline is not None:
        print("\nLarge Ollama baseline" if baseline_mode == "ollama-large-only" else "\nCloud-only baseline")
        summarize(baseline)


if __name__ == "__main__":
    main()
