#!/usr/bin/env bash
set -e
if [ -r /etc/profile.d/eda.sh ]; then
    source /etc/profile.d/eda.sh
fi
eda_workspace_bin=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "${EDA_PYTHON:-python3}" "$eda_workspace_bin/../tools/workspace.py" "$@"
