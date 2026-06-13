#!/bin/bash
# Wrapper para el agendador local (launchd). Corre el ciclo determinista y avisa
# por Telegram solo si hay algo notable. Sin tokens de Claude. Sin git push.
# Logs en logs/cycle.log (gitignored).
set -euo pipefail
ROOT="/Users/itchile/Downloads/[Personal]/fh-dev/claude-tradebot"
cd "$ROOT"
mkdir -p logs
echo "===== $(date '+%Y-%m-%d %H:%M:%S') =====" >> logs/cycle.log
"$ROOT/.venv/bin/python" scripts/run_cycle.py --notify >> logs/cycle.log 2>&1
