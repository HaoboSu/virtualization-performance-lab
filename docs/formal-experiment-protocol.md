# Formal Experiment Protocol

## Objective

Measure how increasing CPU pressure in `contention-vm` changes Sysbench CPU throughput, mean latency and P95 latency in `benchmark-vm`.

The independent variable is the CPU load configured inside the neighboring VM. It is not a direct measurement of total host CPU utilization.

> **Protocol status:** Formal-v1 collection is complete at **50/50 trials**. This document is retained as the pre-specified collection protocol. Final results are reported in [formal-v1-results.md](formal-v1-results.md).

## Design

| Item | Formal-v1 setting |
|---|---|
| Load conditions | 0%, 25%, 50%, 75%, 100% |
| Initial repetitions | 10 per condition |
| Total measured trials | 50 |
| Benchmark duration | 30 seconds |
| Benchmark warm-up | 5 seconds |
| Contention window | 120 seconds |
| Contention method | `stress-ng --cpu-method int64`, 2 workers |
| Load settling before VM1 launch | Wait 10 seconds after VM2 prints `started_at` |
| Required load coverage | Warm-up and measurement, with at least 5 seconds before warm-up and after measurement |
| Inter-trial cooldown | At least 10 seconds after contention ends |
| Benchmark VM | 1 vCPU, 2 GB RAM |
| Contention VM | 2 vCPU, 2 GB RAM |
| Host scheduling | VMware/Windows default; no process affinity |
| Host power | AC power; Windows Balanced plan |

This revision follows smoke-v1's timing failure and precedes formal data collection. New logs carry `collection_protocol: cpu_fixed_v1`. Run the [smoke-v2 rehearsal](smoke-v2-quickstart.md) under these settings before starting the formal schedule. Do not combine pilot/smoke-v1 observations with this dataset because the load method changed.

Formal-v1 used ten repetitions per condition, as specified here. Any future extension to 20 repetitions per condition should be treated as a separate follow-on dataset rather than silently changing the completed Formal-v1 result.

## Why use blocked randomization

Each block contains all five load conditions exactly once, in a randomized order. This spreads every condition across the experiment timeline and reduces the chance that one load level is always measured when the laptop is hotter or background activity is different.

Generate a reproducible 10-run-per-condition schedule from the repository root:

```bash
python3 scripts/generate_schedule.py \
  --repetitions 10 \
  --seed 20260914 \
  --output experiments/formal_v1_schedule.csv
```

The seed is part of the protocol and should not be changed after data collection begins.

## Pre-experiment controls

Before every session:

1. Connect the laptop to AC power.
2. Use the recorded Windows Balanced plan; record any separate power-mode slider setting and keep it unchanged.
3. Close unnecessary host applications and pause updates, downloads and cloud synchronization.
4. Start both VMs and wait at least five minutes before collecting results.
5. Confirm that VM CPU and RAM settings have not changed.
6. Confirm that no earlier `stress-ng` process is still active on `contention-vm`:

   ```bash
   pgrep -a stress-ng
   ```

7. Record any unusual host activity, interruption or thermal concern in the session notes.
8. On both VMs, run `timedatectl status` and confirm synchronization. New logs record `clock_synchronized`; analysis requires `yes`. This is not an exact clock-offset measurement.
9. Use matching versions of both collection scripts and the analysis modules. Record the repository revision in session notes; the scripts also include their local revision in every new log.

## Per-trial procedure

Follow `experiments/formal_v1_schedule.csv` from top to bottom.

### Baseline trial (0%)

Keep `contention-vm` powered on but idle. On `benchmark-vm`, run:

```bash
./scripts/run_benchmark.sh 0 <run-number> formal_v1
```

### Contention trial (25%, 50%, 75% or 100%)

On `contention-vm`, start a 120-second load window using the fixed `int64` method. Use the same run number and study name as the matching benchmark trial:

```bash
./scripts/run_contention.sh <load> <run-number> formal_v1
```

After VM2 prints `started_at`, wait 10 seconds, switch to `benchmark-vm` and run:

```bash
./scripts/run_benchmark.sh <load> <run-number> formal_v1
```

Example for the third 75% trial:

```bash
./scripts/run_contention.sh 75 3 formal_v1
```

and on `benchmark-vm`:

```bash
./scripts/run_benchmark.sh 75 3 formal_v1
```

Wait at least 10 seconds after the contention command finishes before starting the next scheduled trial.

Both scripts refuse to overwrite an existing result or contention log. If a trial is interrupted, preserve the incomplete `.tmp` file, record the reason, and rerun that trial only after deciding how it will be documented.

Before rerunning, move the rejected files from both VMs into a separately named audit directory outside the analyzed `formal_v1` directories, retaining their original names and the exclusion reason. Do not delete or overwrite failed attempts. Analyzed directories must contain exactly the accepted scheduled trials and no `.tmp` files.

## Session split

The default schedule places five blocks in each session:

- Session 1: blocks 1–5, 25 trials;
- Session 2: blocks 6–10, 25 trials.

Using two sessions limits one continuous measurement period while keeping every session balanced across all five conditions.

## Analysis

Copy the matching VM2 logs into `results/contention/formal_v1/` on the analysis machine, alongside VM1's raw logs. For each nonzero-load trial there must be one corresponding VM2 log. A baseline needs no VM2 load log; keep VM2 powered on and idle.

After all scheduled trials are complete, run:

```bash
python3 analysis/analyze_results.py \
  --raw-dir results/raw/formal_v1 \
  --contention-dir results/contention/formal_v1 \
  --schedule experiments/formal_v1_schedule.csv
```

Generated outputs will be written to:

```text
results/processed/formal_v1_results.csv
results/processed/formal_v1_summary.csv
results/processed/formal_v1_coverage.csv
figures/formal_v1/
```

Analysis checks the schedule, matching study/load/run metadata, complete logs, configured durations, fixed load method, worker count, clock synchronization status and consistent settings within each VM. It rejects load windows with less than 5 seconds of margin before VM1's warm-up or after measurement, and rejects baseline overlap with any recorded load window. These are checks against recorded wall-clock windows, not direct measurements of host CPU utilization or guarantees of exact clock alignment. Continue the manual idle-process check as well.

Any failure stops analysis before writing new CSVs or figures. Previously generated outputs may still exist; use only outputs from a successful analysis of the final accepted dataset.

To validate an incomplete batch without producing experimental summaries:

```bash
python3 analysis/analyze_results.py \
  --raw-dir results/raw/formal_v1 \
  --contention-dir results/contention/formal_v1 \
  --validate-only
```

Omitting `--schedule` here checks only available trials; it does not certify completion. Full formal analysis requires the schedule. SD and CV are `NA` for `n=1`; P95 summaries average per-run P95 values rather than pooling event latencies.
