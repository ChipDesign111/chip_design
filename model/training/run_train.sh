#!/usr/bin/env bash
# Pick the currently least-utilized GPU, isolate to one device, train HAR MLP.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

nvidia-smi --query-gpu=index,utilization.gpu,memory.free --format=csv
GPU=$(nvidia-smi --query-gpu=index,utilization.gpu,memory.free --format=csv,noheader,nounits \
  | awk -F',' '{gsub(/ /,"",$1); gsub(/ /,"",$2); gsub(/ /,"",$3); print $2+0, -$3+0, $1}' \
  | sort -n | head -1 | awk '{print $3}')
echo "Using CUDA_VISIBLE_DEVICES=$GPU"
export CUDA_VISIBLE_DEVICES="$GPU"
exec python model/training/train_har_mlp.py "$@"
