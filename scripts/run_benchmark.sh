#!/usr/bin/env bash

set -euo pipefail

usage() {
    echo "Usage: $0 <load: 0|25|50|75|100> <run-number> [study-name]"
    echo "Example: $0 25 1 formal_v1"
}

if [[ $# -lt 2 || $# -gt 3 ]]; then
    usage >&2
    exit 2
fi

LOAD="$1"
RUN_NUMBER="$2"
STUDY_NAME="${3:-formal_v1}"
DURATION_SECONDS="${DURATION_SECONDS:-30}"
THREADS="${SYSBENCH_THREADS:-1}"
WARMUP_SECONDS="${WARMUP_SECONDS:-5}"

if [[ ! "$LOAD" =~ ^(0|25|50|75|100)$ ]]; then
    echo "ERROR: load must be one of 0, 25, 50, 75 or 100." >&2
    exit 2
fi

if [[ ! "$RUN_NUMBER" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: run-number must be a positive integer." >&2
    exit 2
fi

if [[ ! "$STUDY_NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "ERROR: study-name contains unsupported characters." >&2
    exit 2
fi

if [[ ! "$DURATION_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: DURATION_SECONDS must be a positive integer." >&2
    exit 2
fi

if [[ ! "$THREADS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: SYSBENCH_THREADS must be a positive integer." >&2
    exit 2
fi

if [[ ! "$WARMUP_SECONDS" =~ ^[0-9]+$ ]]; then
    echo "ERROR: WARMUP_SECONDS must be a non-negative integer." >&2
    exit 2
fi

if ! command -v sysbench >/dev/null 2>&1; then
    echo "ERROR: sysbench is not installed or is not in PATH." >&2
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$REPO_ROOT/results/raw/$STUDY_NAME"

if [[ "$LOAD" == "0" ]]; then
    CONDITION="baseline"
else
    CONDITION="contention_${LOAD}"
fi

OUTPUT_FILE="$OUTPUT_DIR/${CONDITION}_run_${RUN_NUMBER}.txt"
TEMP_FILE="${OUTPUT_FILE}.tmp"

mkdir -p "$OUTPUT_DIR"

if [[ -e "$OUTPUT_FILE" || -e "$TEMP_FILE" ]]; then
    echo "ERROR: refusing to overwrite an existing result: $OUTPUT_FILE" >&2
    exit 1
fi

echo "Study: $STUDY_NAME"
echo "Condition: ${LOAD}% neighboring-VM configured CPU load"
echo "Run: $RUN_NUMBER"
echo "Warm-up: ${WARMUP_SECONDS}s"
echo "Measurement: ${DURATION_SECONDS}s"
echo "Output: $OUTPUT_FILE"

{
    echo "study_name: $STUDY_NAME"
    echo "collection_protocol: cpu_fixed_v1"
    echo "configured_neighbor_load_percent: $LOAD"
    echo "run_number: $RUN_NUMBER"
    echo "benchmark_duration_seconds: $DURATION_SECONDS"
    echo "benchmark_threads: $THREADS"
    echo "warmup_seconds: $WARMUP_SECONDS"
    echo "hostname: $(hostname)"
    echo "kernel: $(uname -sr)"
    echo "sysbench_version: $(sysbench --version)"
    echo "clock_synchronized: $(timedatectl show --property=NTPSynchronized --value 2>/dev/null || echo unknown)"
    echo "repository_revision: $(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "warmup_started_at: $(date --iso-8601=ns)"
    if (( WARMUP_SECONDS > 0 )); then
        sysbench cpu --threads="$THREADS" --time="$WARMUP_SECONDS" run >/dev/null
    fi
    echo "warmup_finished_at: $(date --iso-8601=ns)"
    echo "started_at: $(date --iso-8601=ns)"
    echo
    sysbench cpu --threads="$THREADS" --time="$DURATION_SECONDS" run
    echo
    echo "finished_at: $(date --iso-8601=ns)"
    echo "exit_status: 0"
} 2>&1 | tee "$TEMP_FILE"

mv "$TEMP_FILE" "$OUTPUT_FILE"
echo "Saved: $OUTPUT_FILE"
