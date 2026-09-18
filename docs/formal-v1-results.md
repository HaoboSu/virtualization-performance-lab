# Formal v1 Results

## Experimental validity

Formal v1 contains 50 VM1 benchmark observations: 10 matched runs at each configured neighbor CPU load (0%, 25%, 50%, 75%, and 100%).  
The four non-baseline conditions have 40 corresponding VM2 contention logs.

All VM1 benchmark processes and all VM2 contention processes exited successfully. The VM2 contention interval covered the full VM1 warm-up and benchmark window in all 40 non-baseline observations. No VM2 log reported failed or untrustworthy stress-ng metrics.

Because run numbers 1–10 form matched blocks across all five load conditions, the analysis treats the design as repeated / paired rather than as 50 fully independent observations.

## Main performance result

| Neighbor CPU load | Mean throughput (events/s) | Change vs baseline | Mean P95 latency (ms) | Throughput CV |
|---:|---:|---:|---:|---:|
| 0% | 2655.85 | — | 0.466 | 1.75% |
| 25% | 2535.40 | -4.54% | 0.531 | 3.74% |
| 50% | 2476.35 | -6.76% | 0.588 | 4.39% |
| 75% | 2399.01 | -9.67% | 0.643 | 5.01% |
| 100% | 2373.76 | -10.62% | 0.601 | 10.22% |

VM1 throughput declines as configured neighbor CPU contention increases. Mean throughput falls from **2655.85 events/s** at baseline to **2373.76 events/s** at 100% neighbor load, a mean reduction of **10.62%**.

Performance variability also increases. Throughput CV rises from **1.75%** at baseline to **10.22%** at 100% load. This suggests that contention affects both average performance and run-to-run stability.

P95 latency generally increases with contention, although the mean at 100% load is lower than the mean at 75% load. Therefore the latency result should be interpreted as degradation under contention rather than as a strictly monotonic response at every load step.

## Repeated-measures evidence

A Friedman repeated-measures test found differences across the five load levels for throughput (**χ² = 28.16, p = 1.16e-05**) and P95 latency (**χ² = 29.41, p = 6.46e-06**).

Paired comparisons against the same-run baseline were also performed with Holm correction. For throughput, all four contention levels remained statistically distinguishable from baseline after correction.

| Load | Mean paired difference (events/s) | Cohen's dz | Holm-adjusted paired-t p |
|---:|---:|---:|---:|
| 25% | -120.44 | -1.15 | 0.005433 |
| 50% | -179.49 | -1.55 | 0.002554 |
| 75% | -256.83 | -1.95 | 0.0006493 |
| 100% | -282.09 | -1.34 | 0.004265 |

## Robustness / sensitivity analysis

The within-load IQR rule flagged two low-throughput observations:

- 50% load, run 6: **2227.69 events/s**
- 100% load, run 2: **1753.41 events/s**

Both observations are retained in the primary analysis because their VM1 and VM2 logs are technically valid.

A secondary sensitivity analysis excluding only these IQR-flagged observations still gives a mean throughput reduction of **8.03%** at 100% neighbor load. The paired throughput comparisons remain significant after Holm correction. Therefore the principal result is not dependent on the two most extreme observations.

## Trend across matched runs

A simple linear slope was estimated separately within each of the 10 matched run blocks. The mean slope was **-70.06 events/s per additional 25 percentage points of configured neighbor load** (95% CI **-101.67 to -38.44**).

Only 2 of 10 matched runs decreased strictly at every single step from 0% → 25% → 50% → 75% → 100%. This is expected for a noisy systems experiment: the aggregate degradation trend is clear, but individual adjacent steps can overlap because of run-to-run variation.

## Interpretation

The experiment provides evidence that a CPU-intensive neighboring VM can reduce the performance of a colocated VM on the tested VMware Workstation host. In this setup, increasing neighbor CPU contention is associated with:

1. lower average benchmark throughput;
2. higher tail latency overall;
3. greater run-to-run performance variability.

The result is best described as **contention-induced performance degradation and increased variability**, rather than a perfectly linear or deterministic slowdown.

## Limitations

- The chronological collection order matched **48 of 50 scheduled positions**. In block/run 7, the final two conditions were collected as 75% then 0% rather than the scheduled 0% then 75%. Both observations remained valid and the block still contained all five conditions exactly once; the deviation is documented in [formal-v1-final-validation.md](formal-v1-final-validation.md).
- `configured_neighbor_load_percent` is an experimental control setting, not a direct hypervisor CPU-utilization measurement.
- The experiment uses one physical host, one virtualization platform/configuration, and one benchmark workload, so the numerical effect size should not be generalized to all virtualized systems.
- Formal v1 contains 10 matched blocks. This is sufficient to reveal a clear effect in this setup, but larger experiments could characterize tail behavior and rare interference events more precisely.


## Reproducibility

The complete accepted dataset is archived as 50 VM1 benchmark logs and 40 paired VM2 contention logs. From the repository root, install the analysis dependencies and regenerate the final CSVs and figures with:

```bash
python3 -m pip install -r requirements.txt
python3 analysis/analyze_formal_v1.py
```

The final analyzer checks the expected 50/40 file inventory, load/run identities, successful exit status, clock-synchronization metadata, VM2 worker/method configuration, and contention-window coverage before writing final outputs.

The original blocked-randomized schedule remains at `experiments/formal_v1_schedule.csv`. Pilot, smoke-test, and session-1 checkpoint artifacts are retained for provenance but are not pooled into the final Formal-v1 dataset.
