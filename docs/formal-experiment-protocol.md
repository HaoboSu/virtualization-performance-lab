# Formal Experiment Protocol

## Objective

Measure how increasing CPU pressure in `contention-vm` changes Sysbench CPU throughput, mean latency and P95 latency in `benchmark-vm`.

The independent variable is the CPU load configured inside the neighboring VM. It is not a direct measurement of total host CPU utilization.

## Design

| Item | Formal-v1 setting |
|---|---|
| Load conditions | 0%, 25%, 50%, 75%, 100% |
| Initial repetitions | 10 per condition |
| Total measured trials | 50 |
| Benchmark duration | 30 seconds |
| Benchmark warm-up | 5 seconds |
| Contention window | 60 seconds |
| Inter-trial cooldown | At least 10 seconds after contention ends |
| Benchmark VM | 1 vCPU, 2 GB RAM |
| Contention VM | 2 vCPU, 2 GB RAM |
| Host scheduling | VMware/Windows default; no process affinity |

Ten repetitions are the first formal collection stage. The dataset can later be extended to 20 repetitions per condition without changing the file naming or analysis workflow.

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
2. Use the same Windows power mode.
3. Close unnecessary host applications and pause updates, downloads and cloud synchronization.
4. Start both VMs and wait at least five minutes before collecting results.
5. Confirm that VM CPU and RAM settings have not changed.
6. Confirm that no earlier `stress-ng` process is still active on `contention-vm`:

   ```bash
   pgrep -a stress-ng
   ```

7. Record any unusual host activity, interruption or thermal concern in the session notes.

## Per-trial procedure

Follow `experiments/formal_v1_schedule.csv` from top to bottom.

### Baseline trial (0%)

Keep `contention-vm` powered on but idle. On `benchmark-vm`, run:

```bash
./scripts/run_benchmark.sh 0 <run-number> formal_v1
```

### Contention trial (25%, 50%, 75% or 100%)

On `contention-vm`, start a 60-second load window. Use the same run number and study name as the matching benchmark trial:

```bash
./scripts/run_contention.sh <load> <run-number> formal_v1
```

Immediately switch to `benchmark-vm` and run:

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

## Session split

The default schedule places five blocks in each session:

- Session 1: blocks 1–5, 25 trials;
- Session 2: blocks 6–10, 25 trials.

Using two sessions limits one continuous measurement period while keeping every session balanced across all five conditions.

## Analysis

After all scheduled trials are complete, run:

```bash
python3 analysis/analyze_results.py \
  --raw-dir results/raw/formal_v1 \
  --schedule experiments/formal_v1_schedule.csv
```

Generated outputs will be written to:

```text
results/processed/formal_v1_results.csv
results/processed/formal_v1_summary.csv
figures/formal_v1/
```

The analysis stops with an error if it finds a missing, duplicated or unexpected trial relative to the schedule. Do not interpret the formal results until that validation passes and interrupted trials have been reviewed.
