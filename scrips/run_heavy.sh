
#!/usr/bin/env bash

set -euo pipefail



OUT="$HOME/virtualization-performance-lab/results/raw/pilot_v2"

mkdir -p "$OUT"



for i in {1..5}; do

    echo "===== PILOT V2 HEAVY RUN $i ====="

    date -Is

    sysbench cpu --threads=1 --time=30 run | tee "$OUT/heavy_100_run_${i}.txt"

    sleep 10

done

