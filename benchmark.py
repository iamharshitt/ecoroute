import argparse
import json
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Summarize recorded EcoRoute routes.")
    parser.add_argument("results", nargs="?", type=Path, default=Path("output/results.json"))
    args = parser.parse_args()
    try:
        results = json.loads(args.results.read_text(encoding="utf-8"))
        if not isinstance(results, list) or any(
            not isinstance(row, dict) or not isinstance(row.get("routed_to"), str)
            for row in results
        ):
            raise ValueError("expected a JSON array of results with a routed_to string")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Could not read results: {exc}\n")

    routes = Counter(row["routed_to"] for row in results)
    local = routes["Local Edge (Tier 2)"]
    cloud = routes["Cloud (Tier 3)"]
    failed = routes["Error"] + routes["Cloud (Error)"]
    unknown = len(results) - local - cloud - failed
    print(f"Total results: {len(results)}")
    print(f"Handled locally: {local}")
    print(f"Handled in the cloud: {cloud}")
    print(f"Failed: {failed}")
    print(f"Unrecognized route: {unknown}")
    rate = f"{100 * local / len(results):.1f}%" if results else "N/A (no results)"
    print(f"Local share of all results: {rate}")


if __name__ == "__main__":
    main()
