#!/usr/bin/env sh
set -eu

echo "Sakura first-run check"
python -m app.cli.first_run_check "$@"
