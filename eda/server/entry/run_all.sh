#!/usr/bin/env bash
# Optional dispatcher only: the three stages remain independent scripts.
set -euo pipefail
cd -- "$(dirname -- "$0")"
source ./run_env.sh
for eda_arg in "$@"; do
    case "$eda_arg" in --headless) ;; *) echo "Only --headless is accepted" >&2; exit 2;; esac
done
command -v flock >/dev/null || { echo "Missing flock" >&2; exit 2; }
exec 9>"$EDA_UPLOAD/logs/pipeline.lock"
flock -n 9 || { echo "A pipeline is already running in this upload" >&2; exit 2; }
exec > >(tee -a "$EDA_UPLOAD/logs/pipeline.log") 2>&1
rm -f -- "$EDA_UPLOAD/logs/run_exit_code.txt"
finish() {
    eda_code=$?
    printf '%s\n' "$eda_code" > "$EDA_UPLOAD/logs/run_exit_code.txt"
    bash "$EDA_DEPLOY/server/bin/workspace.sh" --root "$EDA_UPLOAD" || true
    exit "$eda_code"
}
trap finish EXIT
bash ./check_env.sh
bash ./run_eda.sh "$@"
bash ./collect_results.sh
