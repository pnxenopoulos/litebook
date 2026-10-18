"""Validate benchmark outcomes without asserting machine-specific speeds."""

import json
import subprocess
import sys

import pytest

from benchmarks.workloads import CASES, prepare


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
@pytest.mark.parametrize("create_orders", [False, True])
def test_python_benchmark_fixture(case, create_orders):
    fixture = prepare(case, create_orders)
    fixture.validate(fixture.run())
    fresh = prepare(case, create_orders)
    fresh.validate(fresh.run())


def test_benchmark_report_and_separate_memory_worker(tmp_path):
    output = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "benchmarks.book",
            "--case",
            "mixed/64",
            "--samples",
            "1",
            "--warmups",
            "0",
            "--batches",
            "1",
            "--latency",
            "--memory-events",
            "120",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(output.read_text())
    assert len(report["results"]) == 2
    for result in report["results"]:
        assert result["events_per_sample"] == 384
        assert result["fills_per_fixture"] == 128
        assert len(result["sample_elapsed_ns"]) == 1
        latency = result["separate_event_latency"]
        assert sum(row["observations"] for row in latency.values()) == 384
        assert latency["add"]["p50_ns"] <= latency["add"]["p99_ns"]
    assert report["memory_replay"]["events"] == 120
    assert report["memory_replay"]["active_orders"] == 64
    assert report["memory_replay"]["expected_filled_orders_retained"] == 80
