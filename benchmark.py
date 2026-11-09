import argparse
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median

LOCAL = "Local Edge (Tier 2)"
CLOUD = "Cloud (Tier 3)"


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

    if not routed or index(routed, "routed") != index(baseline, "cloud-only"):
        raise ValueError("Comparison requires nonempty runs with identical task IDs and prompts.")


def token_total(rows, key):
    values = [row.get(key) for row in rows]
    observed = [value for value in values if type(value) is int and value >= 0]
    if not observed:
        return "unavailable"
    return f"{sum(observed)} observed ({len(observed)}/{len(rows)} results with data)"


def summarize(rows):
    routes = Counter(row["routed_to"] for row in rows)
    local, cloud = routes[LOCAL], routes[CLOUD]
    failed = routes["Error"] + routes["Cloud (Error)"]
    print(f"Total results: {len(rows)}")
    print(f"Handled locally: {local}")
    print(f"Handled in the cloud: {cloud}")
    print(f"Failed: {failed}")
    print(f"Unrecognized route: {len(rows) - local - cloud - failed}")
    rate = f"{100 * local / len(rows):.1f}%" if rows else "N/A (no results)"
    print(f"Local share of all results: {rate}")
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
    print("Cloud input tokens: " + token_total(rows, "cloud_input_tokens"))
    print("Cloud output tokens: " + token_total(rows, "cloud_output_tokens"))


def main():
    parser = argparse.ArgumentParser(description="Summarize EcoRoute runs and optionally compare a matched cloud-only baseline.")
    parser.add_argument("results", nargs="?", type=Path, default=Path("output/results.json"))
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    try:
        routed = load_results(args.results)
        baseline = load_results(args.baseline) if args.baseline else None
        if baseline is not None:
            paired_results(routed, baseline)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Could not compare results: {exc}\n")

    print("EcoRoute results")
    summarize(routed)
    if baseline is not None:
        print("\nCloud-only baseline")
        summarize(baseline)


if __name__ == "__main__":
    main()

