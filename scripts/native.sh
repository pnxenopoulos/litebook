#!/usr/bin/env bash
# Match native tests/benchmarks to the interpreter used by the extension.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYO3_PYTHON
PYO3_PYTHON="$(uv run --no-sync python -c 'import sys; print(sys.executable)')"
python_libdir="$(uv run --no-sync python -c 'import sys, sysconfig; print(sysconfig.get_config_var("LIBDIR") or sys.base_prefix)')"
case "$(uname -s)" in
    Linux*) export LD_LIBRARY_PATH="${python_libdir}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" ;;
    Darwin*) export DYLD_LIBRARY_PATH="${python_libdir}${DYLD_LIBRARY_PATH:+:${DYLD_LIBRARY_PATH}}" ;;
    *) export PATH="${python_libdir}:${PATH}" ;;
esac
cargo "$@"
