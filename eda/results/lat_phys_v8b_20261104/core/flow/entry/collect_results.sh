#!/usr/bin/env bash
# Stage 3: generate readable reports and checked delivery/review archives.
set -euo pipefail
cd -- "$(dirname -- "$0")"
source ./run_env.sh
exec > >(tee -a "$EDA_UPLOAD/logs/collect.log") 2>&1
finish() {
    eda_code=$?
    printf '%s\n' "$eda_code" > "$EDA_UPLOAD/logs/collect_exit_code.txt"
    bash "$EDA_DEPLOY/server/bin/workspace.sh" --root "$EDA_UPLOAD" || true
    exit "$eda_code"
}
trap finish EXIT
bash "$EDA_DEPLOY/server/bin/eda.sh" report --work "$EDA_WORK"
bash "$EDA_DEPLOY/server/bin/eda.sh" package --work "$EDA_WORK"
bash "$EDA_DEPLOY/server/bin/review.sh" --work "$EDA_WORK"
