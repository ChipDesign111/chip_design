#!/usr/bin/env bash
set -e
if [ -r /etc/profile.d/eda.sh ]; then
    source /etc/profile.d/eda.sh
fi
eda_script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "${EDA_PYTHON:-python3}" "$eda_script_dir/flow.py" "$@"
