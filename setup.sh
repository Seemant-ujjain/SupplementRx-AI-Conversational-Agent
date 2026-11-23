#!/usr/bin/env bash
# One-time setup: Python environment, prepared text, MedCPT models and search indexes. Safe to rerun.
set -euo pipefail
cd "$(dirname "$0")"
python=supplementsrx_env/bin/python

if [ ! -x "$python" ]; then
  if command -v python3.12 >/dev/null; then
    python3.12 -m venv supplementsrx_env
  elif command -v uv >/dev/null; then
    uv venv --seed --python 3.12 supplementsrx_env
  else
    echo "Python 3.12 is needed. Install it (macOS: brew install python@3.12) and run this again." >&2
    exit 1
  fi
fi

echo "1/3 Installing libraries"
if "$python" -m pip --version >/dev/null 2>&1; then
  "$python" -m pip install -q -r requirements-search.txt
else  # environment made by uv without pip
  uv pip install -q --python "$python" -r requirements-search.txt
fi
echo "2/3 Preparing text from the knowledge graph"
"$python" scripts/prepare_indexing_inputs.py >/dev/null
echo "3/3 Building search indexes (the first run downloads about 1.6 GB of models)"
"$python" scripts/build_search_index.py
echo "Done. Start searching with: ./search"
