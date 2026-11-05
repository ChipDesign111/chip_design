#!/usr/bin/env bash
# Stage 1: freeze this upload's inputs and check tools, libraries and display.
set -euo pipefail
cd -- "$(dirname -- "$0")"
source ./run_env.sh
exec > >(tee -a "$EDA_UPLOAD/logs/environment.log") 2>&1
finish() {
    eda_code=$?
    printf '%s\n' "$eda_code" > "$EDA_UPLOAD/logs/environment_exit_code.txt"
    bash "$EDA_DEPLOY/server/bin/workspace.sh" --root "$EDA_UPLOAD" || true
    exit "$eda_code"
}
trap finish EXIT
if [ ! -d "$EDA_WORK" ]; then
    bash "$EDA_DEPLOY/server/bin/eda.sh" prepare --work "$EDA_WORK" --config "$EDA_CONFIG"
fi
bash "$EDA_DEPLOY/server/bin/eda.sh" doctor --work "$EDA_WORK"
