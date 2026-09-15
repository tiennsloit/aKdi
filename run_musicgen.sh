#!/bin/bash
set -e

# Always run from the project folder, no matter where it is invoked from.
cd "$(dirname "$0")"

source /home/joseph/miniconda3/etc/profile.d/conda.sh
conda activate musicgen

# Prevent Paddle's cuDNN libraries from being used.
unset LD_LIBRARY_PATH

# Use the musicgen env's Python explicitly (never the base interpreter).
exec /home/joseph/miniconda3/envs/musicgen/bin/python /home/joseph/musicgen/musicgen_api.py
