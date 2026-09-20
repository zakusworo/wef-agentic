#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export WEF_AGENTIC_DEMO=1
exec .venv/bin/streamlit run src/wef_agentic/ui/streamlit_app.py \
  --server.address 127.0.0.1 --server.port "${WEF_DEMO_PORT:-8501}" \
  --server.headless true --browser.gatherUsageStats false
