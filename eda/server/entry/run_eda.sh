#!/usr/bin/env bash
# Stage 2: run or resume synthesis and Innovus stages 01-34 in this upload.
set -euo pipefail
cd -- "$(dirname -- "$0")"
source ./run_env.sh
for eda_arg in "$@"; do
    case "$eda_arg" in --headless) ;; *) echo "Only --headless is accepted" >&2; exit 2;; esac
done
exec > >(tee -a "$EDA_UPLOAD/logs/flow.log") 2>&1
finish() {
    eda_code=$?
    printf '%s\n' "$eda_code" > "$EDA_UPLOAD/logs/eda_exit_code.txt"
    bash "$EDA_DEPLOY/server/bin/workspace.sh" --root "$EDA_UPLOAD" || true
    exit "$eda_code"
}
trap finish EXIT
if [ ! -d "$EDA_WORK" ]; then
    echo "Run bash ./check_env.sh first" >&2
    exit 2
fi
bash "$EDA_DEPLOY/server/bin/eda.sh" all --work "$EDA_WORK" "$@"
