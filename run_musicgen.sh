#!/bin/bash

source /home/joseph/miniconda3/etc/profile.d/conda.sh

conda activate musicgen

# Prevent Paddle's cuDNN libraries from being used.
unset LD_LIBRARY_PATH

exec python /home/joseph/musicgen/musicgen_api.py
