# Formal-v1 Final Validation

Date: 2026-09-18

This document records the final seal-check of the completed Formal-v1 dataset and repository state.

## Dataset inventory

- VM1 benchmark logs: **50** (`results/raw/formal_v1/`)
- VM2 contention logs: **40** (`results/contention/formal_v1/`)
- VM1 conditions: 0%, 25%, 50%, 75%, 100%, with runs 1–10 present at every level
- VM2 conditions: 25%, 50%, 75%, 100%, with runs 1–10 present at every non-baseline level
- No VM2 log is expected for baseline trials

The full 50-trial identity set matches `experiments/formal_v1_schedule.csv`.

## Metadata and execution checks

All accepted VM1 logs record:

- `study_name: formal_v1`
- `collection_protocol: cpu_fixed_v1`
- hostname `benchmark-vm`
- kernel `Linux 6.8.0-139-generic`
- `sysbench 1.0.20`
- 30-second benchmark duration
- one benchmark thread
- five-second warm-up
- synchronized clock status `yes`
- repository revision `97c28ca6a3d61920e24cba6466d7555f03369b10`
- `exit_status: 0`

All accepted VM2 logs record:

- `study_name: formal_v1`
- `collection_protocol: cpu_fixed_v1`
- hostname `contention-vm`
- kernel `Linux 6.8.0-139-generic`
- `stress-ng 0.17.06`
- 120-second contention duration
- two CPU workers
- CPU method `int64`
- synchronized clock status `yes`
- the same repository revision
- `exit_status: 0`

Every VM2 run reports zero failed workers and zero untrustworthy metrics.

## Pairing and timing coverage

All 40 non-baseline VM1 trials have exactly one matching VM2 log with the same load and run number.

All 40 VM2 contention windows cover the full paired VM1 warm-up and benchmark measurement window.

Recorded margins across the 40 non-baseline trials:

- minimum VM2 start-to-VM1 warm-up margin: **8.977611 s**
- maximum VM2 start-to-VM1 warm-up margin: **23.737548 s**
- minimum VM1 benchmark-end-to-VM2 end margin: **61.262577 s**
- maximum VM1 benchmark-end-to-VM2 end margin: **75.975378 s**

Every pair therefore exceeds the protocol's required five-second coverage margin on both sides.

No baseline benchmark overlaps a recorded VM2 contention window, and no benchmark overlaps a different trial's VM2 contention window.

The smallest recorded gap between the end of one trial window and the start of the next is **22.248627 s**, exceeding the protocol's ten-second inter-trial cooldown requirement.

## Schedule-order audit

All 50 scheduled trial identities were collected. The chronological order matches the fixed schedule at **48 of 50 positions**.

One within-block order deviation is present in block/run 7:

- scheduled final two conditions: **0% then 75%**
- observed final two conditions: **75% then 0%**

This is a documented protocol deviation, not a missing or invalid observation. Both trials have valid metadata, successful execution, no cross-trial overlap, and very large separation from neighboring trials. The block remains balanced because all five conditions are present exactly once. The paired/repeated-measures analysis is based on matched run identity rather than chronological adjacency, so these observations are retained in the primary dataset.

## Analysis artifacts

The repository contains the completed analysis entry point:

```bash
python3 -m pip install -r requirements.txt
python3 analysis/analyze_formal_v1.py
```

`requirements.txt` includes NumPy, pandas, SciPy, and Matplotlib required by the final analyzer.

Final processed outputs include:

- `formal_v1_results.csv`
- `formal_v1_coverage.csv`
- `formal_v1_summary.csv`
- `formal_v1_statistical_tests.csv`
- `formal_v1_friedman_tests.csv`
- `formal_v1_sensitivity_summary.csv`
- `formal_v1_sensitivity_tests.csv`
- `formal_v1_iqr_outliers.csv`
- `formal_v1_run_level_slopes.csv`
- `formal_v1_direction_consistency.csv`

Final figures are stored under `figures/formal_v1/`.

## Historical records

`docs/formal-v1-session1-validation.md` is intentionally retained as a historical checkpoint describing the first 25 trials before Formal-v1 was completed. It is now explicitly marked as historical and points readers to the completed Formal-v1 results.

The current project status is defined by `README.md`, this final validation record, and `docs/formal-v1-results.md`.

## Seal-check conclusion

Formal-v1 is complete for its stated scope. The accepted dataset contains all planned condition/run identities, valid VM1/VM2 pairing, successful executions, valid load-window coverage, final statistical analysis, sensitivity analysis, figures, raw-data archives, processed outputs, and documented limitations.

No additional trials are required to complete Formal-v1. Any future host telemetry, additional repetitions, alternative hypervisors, custom latency benchmarks, or other resource-contention experiments should be treated as separate extensions rather than unfinished Formal-v1 work.
