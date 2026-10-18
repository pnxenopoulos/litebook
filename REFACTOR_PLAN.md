# Litebook refactor progress

Stage one establishes a correct, reproducible baseline before changing storage,
matching algorithms, or Python API granularity. Each chunk has its own pull request.
Review and merge them in order; later branches start from the preceding branch.

## Review sequence

| Chunk | Branch | Scope | Status |
| --- | --- | --- | --- |
| 1 | `codex/stage1-rebuild` | Build configuration, locked release rebuild, this tracker | [PR #7](https://github.com/pnxenopoulos/litebook/pull/7) ready for review |
| 2 | `codex/stage1-correctness` | Correctness fixes, regression and reference-model tests | [PR #8](https://github.com/pnxenopoulos/litebook/pull/8) ready for review |
| 3 | `codex/stage1-benchmarks` | Native and Python workloads, reproducible baseline results | [PR #9](https://github.com/pnxenopoulos/litebook/pull/9) ready for review |

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
- [x] Open PR and record validation.

Validation: a fresh release rebuild passes all 13 existing Python tests on CPython 3.11.8
with Rust 1.96.1. Rust formatting, Clippy, and Python import-order checks pass.

## Chunk 2 correctness

- [x] Assign fill buyer and seller IDs by side, for either resting side.
- [x] Reject duplicate submissions without changing book state.
- [x] Reject non-finite or non-positive prices, quantities, and tick sizes; check
  price-to-tick conversion bounds before casting.
- [x] Prevent fills or submissions involving completed orders and zero quantities.
- [x] Return false when canceling a filled or already canceled order.
- [x] Preserve FIFO, seller-limit execution prices, nearest-tick rounding, detached
  Python order snapshots, and lookup of filled orders.
- [x] Fix fractional-price book display and test it.
- [x] Add deterministic regressions and randomized comparison with a simple reference
  model, checking quantities, fills, FIFO, and book/index consistency.
- [x] Rebuild, run required checks, and open PR.

Duplicate-ID protection covers IDs still known to the book. Permanent rejection of
all previously canceled IDs would require retained tombstones and is deferred.

Validation: regressions produced 23 failures before fixes. The release extension now
passes 50 tests, including 150 deterministic Hypothesis histories compared with an
independent list-based model. See [behavior rules](docs/semantics.md).

## Chunk 3 baseline benchmarks

- [x] Add Criterion benchmarks with fresh mutable fixtures, consumed outputs, and
  explicit operation counts.
- [x] Cover resting insertion, cancellation at varied queue depths, partial fills,
  multi-level sweeps, and deterministic mixed event replay.
- [x] Measure Python creation plus submission separately from pre-created-order
  submission; reset state for each sample.
- [x] Use monotonic timers, warmup, repeated samples, fixed seeds, and machine/build
  metadata. Keep per-event latency sampling separate from throughput timing.
- [x] Record sustained replay memory behavior and explain retained filled-order history.
- [x] Smoke-test benchmark fixtures and run representative release baselines.
- [x] Document commands, results, limitations, and PR link.

Absolute throughput is machine- and workload-specific. Shared CI runs validate
fixtures and execution; performance comparisons require equivalent builds and hardware.

Validation: 71 Python tests and the native fixture integration test pass; formatting,
Clippy across all targets, Python import ordering, and both benchmark smoke suites pass.
Recorded 10 native cases (20 samples each) and 20 Python case/mode combinations
(7 samples each), plus separate latency sampling and a 60,000-event memory replay.
See [baseline results](benchmarks/BASELINE.md) and [methodology](benchmarks/README.md).

## Later stages

- [ ] Extract a Python-independent core and introduce typed batch submission/output.
- [ ] Store each live order once, with reusable handles and direct cancellation links.
- [ ] Separate active state from historical retention and reuse output storage.
- [ ] Compare tree, dense, and paged price indexes on the established workloads.
- [ ] Profile allocations/cache behavior; evaluate compiler tuning and parallel books.

## Stack review and merge

Review PRs in numeric order. Each PR changes only its own chunk relative to its base.
After squash/rebase merges, rebase and retarget descendants before merging them so
already-reviewed commits do not reappear in later diffs. No PR is merged automatically.
