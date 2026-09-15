#!/usr/bin/env bash

set -euo pipefail

usage() {
    echo "Usage: $0 <load: 25|50|75|100> <run-number> [study-name]"
    echo "Example: $0 75 3 formal_v1"
}

if [[ $# -lt 2 || $# -gt 3 ]]; then
    usage >&2
    exit 2
fi

LOAD="$1"
RUN_NUMBER="$2"
STUDY_NAME="${3:-formal_v1}"
DURATION_SECONDS="${CONTENTION_DURATION_SECONDS:-120}"
CPU_WORKERS="${CPU_WORKERS:-2}"
CPU_METHOD="int64"

if [[ ! "$LOAD" =~ ^(25|50|75|100)$ ]]; then
    echo "ERROR: load must be one of 25, 50, 75 or 100." >&2
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
    echo "ERROR: CONTENTION_DURATION_SECONDS must be a positive integer." >&2
    exit 2
fi

if [[ ! "$CPU_WORKERS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: CPU_WORKERS must be a positive integer." >&2
    exit 2
fi

if ! command -v stress-ng >/dev/null 2>&1; then
    echo "ERROR: stress-ng is not installed or is not in PATH." >&2
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$REPO_ROOT/results/contention/$STUDY_NAME"
OUTPUT_FILE="$OUTPUT_DIR/contention_${LOAD}_run_${RUN_NUMBER}.txt"
TEMP_FILE="${OUTPUT_FILE}.tmp"

mkdir -p "$OUTPUT_DIR"

if [[ -e "$OUTPUT_FILE" || -e "$TEMP_FILE" ]]; then
    echo "ERROR: refusing to overwrite an existing log: $OUTPUT_FILE" >&2
    exit 1
fi

echo "Starting ${CPU_WORKERS} stress-ng CPU workers at ${LOAD}% configured load (${CPU_METHOD})"
echo "Duration: ${DURATION_SECONDS}s"
echo "Output: $OUTPUT_FILE"
echo "After started_at appears, wait 10 seconds, then start run_benchmark.sh on benchmark-vm."

{
    echo "study_name: $STUDY_NAME"
    echo "collection_protocol: cpu_fixed_v1"
    echo "configured_load_percent: $LOAD"
    echo "run_number: $RUN_NUMBER"
    echo "contention_duration_seconds: $DURATION_SECONDS"
    echo "cpu_workers: $CPU_WORKERS"
    echo "cpu_method: $CPU_METHOD"
    echo "hostname: $(hostname)"
    echo "kernel: $(uname -sr)"
    echo "stress_ng_version: $(stress-ng --version)"
    echo "clock_synchronized: $(timedatectl show --property=NTPSynchronized --value 2>/dev/null || echo unknown)"
    echo "repository_revision: $(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "started_at: $(date --iso-8601=ns)"
    echo
    stress-ng \
        --cpu "$CPU_WORKERS" \
        --cpu-load "$LOAD" \
        --cpu-method "$CPU_METHOD" \
        --timeout "${DURATION_SECONDS}s" \
        --metrics-brief
    echo
    echo "finished_at: $(date --iso-8601=ns)"
    echo "exit_status: 0"
} 2>&1 | tee "$TEMP_FILE"

mv "$TEMP_FILE" "$OUTPUT_FILE"
echo "Saved: $OUTPUT_FILE"
