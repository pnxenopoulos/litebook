# Litebook refactor progress

Stage one establishes a correct, reproducible baseline before changing storage,
matching algorithms, or Python API granularity. Each chunk has its own pull request.
Review and merge them in order; later branches start from the preceding branch.

## Review sequence

| Chunk | Branch | Scope | Status |
| --- | --- | --- | --- |
| 1 | `codex/stage1-rebuild` | Build configuration, locked release rebuild, this tracker | In progress |
| 2 | `codex/stage1-correctness` | Correctness fixes, regression and reference-model tests | Planned |
| 3 | `codex/stage1-benchmarks` | Native and Python workloads, reproducible baseline results | Planned |

Update this file in each PR with its link, validation, completed work, and remaining
work. PRs remain unmerged until reviewed.

## Chunk 1 rebuild

- [x] Inspect the existing Rust implementation, tests, and benchmark scripts.
- [x] Reproduce the pre-existing environment result: 12 passing tests and one
  default-constructor failure, despite the checked-out source declaring a default.
- [x] Give the native library an explicit module name and library targets.
- [x] Keep the extension-module linking feature scoped to Python builds so native
  Rust tests and benchmarks can link Python normally.
- [x] Treat Maturin as a locked Python development/build tool, not a Rust runtime dependency.
- [x] Add a rebuild script that fails before tests if rebuilding fails.
- [x] Regenerate lockfiles, rebuild, and validate the imported extension.
- [ ] Open PR and record validation.

Validation: a fresh release rebuild passes all 13 existing Python tests on CPython 3.11.8
with Rust 1.96.1. Rust formatting, Clippy, and Python import-order checks pass.

## Chunk 2 correctness

- [ ] Assign fill buyer and seller IDs by side, for either resting side.
- [ ] Reject duplicate submissions without changing book state.
- [ ] Reject non-finite or non-positive prices, quantities, and tick sizes; check
  price-to-tick conversion bounds before casting.
- [ ] Prevent fills or submissions involving completed orders and zero quantities.
- [ ] Return false when canceling a filled or already canceled order.
- [ ] Preserve FIFO, seller-limit execution prices, nearest-tick rounding, detached
  Python order snapshots, and lookup of filled orders.
- [ ] Fix fractional-price book display and test it.
- [ ] Add deterministic regressions and randomized comparison with a simple reference
  model, checking quantities, fills, FIFO, and book/index consistency.
- [ ] Rebuild, run required checks, and open PR.

Duplicate-ID protection covers IDs still known to the book. Permanent rejection of
all previously canceled IDs would require retained tombstones and is deferred.

## Chunk 3 baseline benchmarks

- [ ] Add Criterion benchmarks with fresh mutable fixtures, consumed outputs, and
  explicit operation counts.
- [ ] Cover resting insertion, cancellation at varied queue depths, partial fills,
  multi-level sweeps, and deterministic mixed event replay.
- [ ] Measure Python creation plus submission separately from pre-created-order
  submission; reset state for each sample.
- [ ] Use monotonic timers, warmup, repeated samples, fixed seeds, and machine/build
  metadata. Keep per-event latency sampling separate from throughput timing.
- [ ] Record sustained replay memory behavior and explain retained filled-order history.
- [ ] Smoke-test benchmark fixtures and run representative release baselines.
- [ ] Document commands, results, limitations, and PR link.

Absolute throughput is machine- and workload-specific. Shared CI runs validate
fixtures and execution; performance comparisons require equivalent builds and hardware.

## Later stages

- [ ] Extract a Python-independent core and introduce typed batch submission/output.
- [ ] Store each live order once, with reusable handles and direct cancellation links.
- [ ] Separate active state from historical retention and reuse output storage.
- [ ] Compare tree, dense, and paged price indexes on the established workloads.
- [ ] Profile allocations/cache behavior; evaluate compiler tuning and parallel books.
