"""Repeated Python API timings with independent fixtures and optional memory replay."""

import argparse
import gc
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import litebook as lb
import litebook.litebook as native

from benchmarks.workloads import CASES, Random, create, prepare, trace


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def metadata():
    cpu = platform.processor()
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        cpu = next(
            (
                line.split(":", 1)[1].strip()
                for line in cpuinfo.read_text().splitlines()
                if line.startswith("model name")
            ),
            cpu,
        )
    return {
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "revision": command("git", "rev-parse", "HEAD"),
        "tracked_changes": subprocess.run(
            ["git", "diff", "--quiet", "HEAD"], check=False
        ).returncode
        != 0,
        "python": sys.version,
        "python_optimization": sys.flags.optimize,
        "rustc": command("rustc", "--version"),
        "platform": platform.platform(),
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "cpu_affinity": sorted(os.sched_getaffinity(0))
        if hasattr(os, "sched_getaffinity")
        else None,
        "litebook_version": importlib.metadata.version("litebook"),
        "native_extension": str(Path(native.__file__).resolve()),
        "native_sha256": hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(Path("src/lib.rs").read_bytes()).hexdigest(),
        "cargo_lock_sha256": hashlib.sha256(
            Path("Cargo.lock").read_bytes()
        ).hexdigest(),
        "uv_lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "rustflags": os.environ.get("RUSTFLAGS", ""),
    }


def percentiles(values):
    ordered = sorted(values)
    return {
        f"p{p}_ns": ordered[max(0, (len(ordered) * p + 99) // 100 - 1)]
        for p in (50, 95, 99)
    }


def event_latencies(case, create_orders, batches):
    durations = {"add": [], "cancel": []}
    for _ in range(batches):
        fixture = prepare(case, create_orders)
        fills = cancels = 0
        for action, payload in fixture.events:
            started = time.perf_counter_ns()
            if action == "add":
                if create_orders:
                    order = create(fixture.book, payload)
                    fixture.ids.append(order.id)
                else:
                    order = payload
                fills += len(fixture.book.add(order))
            else:
                order_id = fixture.ids[payload] if create_orders else payload
                cancels += fixture.book.cancel(order_id)
            elapsed = time.perf_counter_ns() - started
            durations[action].append(elapsed)
        fixture.validate((fills, cancels))
    return {
        action: {"observations": len(values), **percentiles(values)}
        for action, values in durations.items()
        if values
    }


def benchmark(case, create_orders, samples, warmups, batches, latency):
    timings = []
    for sample in range(samples + warmups):
        fixtures = [prepare(case, create_orders) for _ in range(batches)]
        # Keep GC policy identical across runs; report it with the results.
        was_enabled = gc.isenabled()
        gc.disable()
        try:
            started = time.perf_counter_ns()
            outcomes = [fixture.run() for fixture in fixtures]
            elapsed = time.perf_counter_ns() - started
        finally:
            if was_enabled:
                gc.enable()
        for fixture, outcome in zip(fixtures, outcomes):
            fixture.validate(outcome)
        if sample >= warmups:
            timings.append(elapsed)
    shape = trace(case)
    count = len(shape.commands) * batches
    normalized = [elapsed / count for elapsed in timings]
    result = {
        "case": case.name,
        "mode": "create-add" if create_orders else "precreated",
        "seed_orders": len(shape.seeds),
        "events_per_fixture": len(shape.commands),
        "fills_per_fixture": shape.fills,
        "cancels_per_fixture": shape.cancels,
        "active_after_fixture": shape.active,
        "events_per_sample": count,
        "sample_elapsed_ns": timings,
        "median_ns_per_event": statistics.median(normalized),
        "median_events_per_second": 1e9 / statistics.median(normalized),
        "min_ns_per_event": min(normalized),
        "max_ns_per_event": max(normalized),
    }
    if latency:
        result["separate_event_latency"] = event_latencies(case, create_orders, batches)
    return result


def rss_bytes():
    status = Path("/proc/self/status")
    if status.exists():
        for line in status.read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    return None


def memory_replay(events):
    book = lb.OrderBook(tick_size=1.0)
    for i in range(64):
        book.add(create(book, (True, 9_990 - i % 8, 1.0)))
    random = Random()
    checkpoints = []
    cycles = events // 6
    for cycle in range(cycles + 1):
        if cycle % max(1, cycles // 4) == 0 or cycle == cycles:
            gc.collect()
            checkpoints.append({"events": cycle * 6, "rss_bytes": rss_bytes()})
        if cycle == cycles:
            break
        bid, ask = 9_990 - random.next() % 8, 10_010 + random.next() % 8
        order = create(book, (True, bid, 1.0))
        first = book.add(order)
        canceled = book.cancel(order.id)
        ask_added = book.add(create(book, (False, ask, 1.0)))
        buy_fills = book.add(create(book, (True, ask, 1.0)))
        bid_added = book.add(create(book, (True, 9_990, 1.0)))
        sell_fills = book.add(create(book, (False, 9_990, 1.0)))
        assert not first and canceled and not ask_added and not bid_added
        assert len(buy_fills) == len(sell_fills) == 1
    active = len(book.buy_orders) + len(book.sell_orders)
    assert active == 64
    return {
        "events": cycles * 6,
        "active_orders": active,
        "expected_filled_orders_retained": cycles * 4,
        "checkpoints": checkpoints,
        "rss_method": "Linux VmRSS; separate fresh process",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--batches", type=int, default=16)
    parser.add_argument(
        "--case", action="append", choices=[case.name for case in CASES]
    )
    parser.add_argument(
        "--mode", choices=["both", "precreated", "create-add"], default="both"
    )
    parser.add_argument(
        "--latency", action="store_true", help="separate instrumented per-event run"
    )
    parser.add_argument("--memory-events", type=int, default=0)
    parser.add_argument("--memory-worker", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.memory_worker is not None:
        print(json.dumps(memory_replay(args.memory_worker)))
        return
    if (
        min(args.samples, args.batches) < 1
        or args.warmups < 0
        or args.memory_events < 0
    ):
        parser.error(
            "samples/batches must be positive; warmups/memory-events must be nonnegative"
        )
    results = []
    for case in CASES:
        if args.case and case.name not in args.case:
            continue
        for create_orders in (False, True):
            if args.mode != "both" and create_orders != (args.mode == "create-add"):
                continue
            result = benchmark(
                case,
                create_orders,
                args.samples,
                args.warmups,
                args.batches,
                args.latency,
            )
            results.append(result)
            print(
                f"{case.name:24s} {result['mode']:10s} {result['median_ns_per_event']:10.1f} ns/event"
            )
    report = {
        "metadata": metadata(),
        "settings": {
            "samples": args.samples,
            "warmups": args.warmups,
            "batches": args.batches,
            "gc_disabled_during_throughput": True,
        },
        "results": results,
    }
    if args.memory_events:
        report["memory_replay"] = json.loads(
            command(
                sys.executable,
                "-m",
                "benchmarks.book",
                "--memory-worker",
                str(args.memory_events),
            )
        )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
