# Stage one baseline results

Recorded on 2026-10-18 from harness revision `5130546b81dbddcd06d9f50a32783c401524cbbc`.
The tracked working tree was clean for both recordings. The reports include source,
lockfile, extension, and native executable hashes; later commits add these results
and documentation without changing the measured engine or harness.

Hardware: AMD Ryzen 7 7800X3D, WSL2 Linux x86_64, CPU affinity restricted to logical
CPU 0. CPython 3.11.8 and Rust 1.96.1. The host was not frequency-locked or isolated
from other applications, so these figures establish a local comparison point.

## Command costs

Values are microseconds per submitted command. Rust uses Criterion's mean estimate
from 20 samples and excludes fixture setup/destruction. Python uses the median of
seven aggregate samples after two warmups, with 16 independent fixtures per sample.
The raw native report also contains confidence intervals and individual sample data.

| Workload | Native Rust mean | Python precreated median | Python create plus add median |
| --- | ---: | ---: | ---: |
| resting_existing/8 | 0.146 | 0.242 | 0.959 |
| resting_existing/512 | 0.115 | 0.219 | 0.880 |
| resting_new/256 | 0.172 | 0.305 | 0.977 |
| cancel/16 | 0.116 | 0.178 | 0.184 |
| cancel/256 | 0.500 | 0.567 | 0.571 |
| cancel/4096 | 13.188 | 14.154 | 14.348 |
| partial/256 | 0.277 | 0.456 | 1.120 |
| sweep/8 | 1.728 | 2.341 | 3.085 |
| sweep/64 | 14.767 | 21.222 | 21.736 |
| mixed/64 | 0.167 | 0.314 | 0.865 |

Sweep rows represent one incoming command producing 8 or 64 fills. Cancellation-only
rows contain no timed order creation in either Python mode. Rust consumes owned orders;
Python precreated mode includes PyO3's argument copy and Python output conversion.
These columns compare complete paths rather than isolating only FFI overhead.

## Sustained memory

A fresh subprocess replayed 60,000 mixed commands against one long-lived
book. Active orders remained at 64; the trace implies
40,000 retained filled orders under the current
lookup contract. Approximate process RSS increased from 22.12 MiB to
30.82 MiB, an increase of 8.70 MiB. This includes allocator
capacity and interpreter/runtime memory, so it is not a per-order allocation estimate.

## Reproduce

```shell
bash scripts/rebuild.sh -q
taskset -c 0 bash scripts/native.sh bench --locked --bench book -- --warm-up-time 0.5 --measurement-time 1 --sample-size 20 --save-baseline stage1
taskset -c 0 uv run --no-sync python -m benchmarks.native_report --output benchmarks/results/native.json
taskset -c 0 uv run --no-sync python -m benchmarks.book --samples 7 --warmups 2 --batches 16 --latency --memory-events 60000 --output benchmarks/results/python.json
```

Choose an allowed CPU on other machines. See [methodology](README.md) for workload
shapes, timing boundaries, and limitations. [Native raw results](results/native.json)
and [Python raw results](results/python.json) include the settings and provenance.
Instrumented per-event add/cancel latency percentiles are in the Python report from
a separate run; aggregate throughput timings do not provide latency percentiles.

The current figures support prioritizing direct cancellation and reducing order
construction/conversion work. Production traces, allocation counts, cache profiles,
and concurrent-reader loads remain future measurements. CI checks fixture correctness
and execution without treating these numbers as portable performance thresholds.
