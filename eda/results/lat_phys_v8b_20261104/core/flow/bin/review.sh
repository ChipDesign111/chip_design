#!/usr/bin/env bash
set -e
if [ -r /etc/profile.d/eda.sh ]; then
  source /etc/profile.d/eda.sh
fi
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
exec "${EDA_PYTHON:-python3}" "$HERE/../tools/light_delivery.py" "$@"
