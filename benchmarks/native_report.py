"""Export Criterion estimates and raw samples alongside reproducibility metadata."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from benchmarks.book import metadata
from benchmarks.workloads import CASES, trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--criterion-root", type=Path, default=Path("target/criterion"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    found = {}
    for path in args.criterion_root.glob("**/new/benchmark.json"):
        identity = json.loads(path.read_text())
        found[identity["full_id"]] = (path.parent, identity)
    rows = []
    for case in CASES:
        directory, identity = found[f"book/{case.name}"]
        estimates = json.loads((directory / "estimates.json").read_text())
        samples = json.loads((directory / "sample.json").read_text())
        shape = trace(case)
        count = len(shape.commands)
        assert identity["throughput"]["Elements"] == count
        mean = estimates["mean"]
        interval = mean["confidence_interval"]
        rows.append(
            {
                "case": case.name,
                "events_per_fixture": count,
                "fills_per_fixture": shape.fills,
                "sample_count": len(samples["times"]),
                "mean_ns_per_event": mean["point_estimate"] / count,
                "confidence_level": interval["confidence_level"],
                "lower_ns_per_event": interval["lower_bound"] / count,
                "upper_ns_per_event": interval["upper_bound"] / count,
                "estimates_ns_per_fixture": estimates,
                "raw_samples": samples,
            }
        )
    binaries = [
        p
        for p in Path("target/release/deps").glob("book-*")
        if p.is_file() and os.access(p, os.X_OK)
    ]
    binary = max(binaries, key=lambda path: path.stat().st_mtime)
    report = {
        "metadata": metadata(),
        "benchmark_binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "results": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for row in rows:
        print(f"{row['case']:24s} {row['mean_ns_per_event']:10.1f} ns/event")


if __name__ == "__main__":
    main()
