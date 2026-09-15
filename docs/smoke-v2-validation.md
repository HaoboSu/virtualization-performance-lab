# Smoke-v2 validation

The five-condition rehearsal passed the collection, pairing, timing, and analysis checks on 2026-09-15. All five benchmark trials are included. Each condition has one observation; this validates the workflow and does not establish a repeatable performance effect or complete the formal experiment.

## Sources and collection settings

The user exported two archives from the VMs:

- `vm1-smoke-v2.zip`: five [benchmark logs](../results/raw/smoke_v2/), one run each at configured neighboring-VM loads of 0%, 25%, 50%, 75%, and 100%.
- `vm2-smoke-v2.zip`: four [contention logs](../results/contention/smoke_v2/), matching the nonzero benchmark conditions.

Both archives passed ZIP CRC checks and an exact file-inventory check. There were no duplicate files or unfinished `.tmp` logs. The nine archived logs are byte-identical to the ZIP entries. No trial was excluded or replaced based on its performance result.

All logs record study `smoke_v2`, protocol `cpu_fixed_v1`, synchronized-clock status `yes`, exit status `0`, and repository revision `97c28ca6a3d61920e24cba6466d7555f03369b10`.

- VM1 records hostname `benchmark-vm`, sysbench 1.0.20, one benchmark thread, a 5-second warm-up, and a 30-second measurement. Reported measurement durations range from 30.0002 to 30.0004 seconds; the prime-number limit is 10000.
- VM2 records hostname `contention-vm`, stress-ng 0.17.06, two CPU workers, method `int64`, and a 120-second configured duration. Every load log reports two passed workers, zero failures, zero untrustworthy metrics, and successful completion.
- Both guests record kernel `Linux 6.8.0-138-generic`. Tool versions and collection settings are consistent across trials within each VM role.

Source archive SHA-256 digests:

```text
vm1-smoke-v2.zip  23a8bc903b9bb4d4d734f23bd43827dc8b027de2f1831b292d3f03e8fb1e4f33
vm2-smoke-v2.zip  3b4a1ab9578f7c20c67cd855fc018a240e6b66b639d6b0995be5c131d5b6bfe4
```

## Timing and inclusion

All recorded times are UTC on 2026-09-15. Each nonzero trial's VM2 window covers VM1's entire warm-up and measurement window, with more than the required five seconds at both ends.

| Configured VM2 load | Load start to warm-up start (s) | Measurement end to load end (s) | Check |
| --- | ---: | ---: | --- |
| 0% | N/A | N/A | No recorded load overlaps the baseline warm-up or measurement |
| 25% | 29.54 | 55.46 | Covered |
| 50% | 13.86 | 71.11 | Covered |
| 75% | 15.18 | 69.78 | Covered |
| 100% | 16.84 | 68.10 | Covered |

Warm-up timestamps precede measurement timestamps and cover the configured duration. There are no cross-trial load overlaps, and the recorded gaps between trials exceed the quickstart's ten-second minimum. The [coverage CSV](../results/processed/smoke_v2_coverage.csv) contains the unrounded calculations at the analyzer's microsecond precision.

These checks use timestamps surrounding commands and guest clock-status metadata. They do not measure the actual offset between guest clocks, the exact instants each stressor becomes active, or physical host CPU utilization. Baseline validation establishes absence of overlap with the supplied load logs; it is not continuous monitoring of all background activity. The logs retain stress-ng's `sched_autogroup_enabled` advisory; it is not a reported execution failure. AC power, any Windows power-mode slider setting, and other host activity are not verified by these ZIPs.

## Observations

| Configured VM2 load | N | Throughput (events/s) | Average latency (ms) | Per-run P95 (ms) | Throughput decrease vs baseline (%) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0% | 1 | 2650.38 | 0.38 | 0.48 | 0.00 |
| 25% | 1 | 2506.77 | 0.40 | 0.57 | 5.42 |
| 50% | 1 | 2557.54 | 0.39 | 0.54 | 3.50 |
| 75% | 1 | 2506.93 | 0.40 | 0.60 | 5.41 |
| 100% | 1 | 2424.90 | 0.41 | 0.58 | 8.51 |

Every field in the [per-run CSV](../results/processed/smoke_v2_results.csv), [summary CSV](../results/processed/smoke_v2_summary.csv), and coverage CSV was reconciled against the raw logs and independent calculations. Throughput and P95 values also agree with the screenshots supplied during collection. The three [figures](../figures/smoke_v2/) were generated from these summaries and visually checked.

With N=1, each mean and median equals the single observation. Sample SD and CV are `NA`; absent error bars do not imply zero variability. Throughput at 50% exceeds that at 25%, and P95 at 100% is below that at 75%. These observations are retained; the rehearsal does not establish a monotonic relationship, statistical significance, or a causal effect size. Figure lines connect measured conditions and do not add observations between them. P95 summaries represent per-run percentiles, not a percentile of pooled event latencies.

The load percentages are stress-ng configuration values inside VM2. Keep this study separate from smoke-v1, whose logs used the default `all` CPU method, and from the pilot and formal datasets. Existing studies and their archived artifacts remain unchanged.

## Reproduce

From the repository root, using the analyzer at collection revision `97c28ca6a3d61920e24cba6466d7555f03369b10`:

```bash
python3 analysis/analyze_results.py \
  --raw-dir results/raw/smoke_v2 \
  --contention-dir results/contention/smoke_v2 \
  --validate-only

MPLBACKEND=Agg python3 analysis/analyze_results.py \
  --raw-dir results/raw/smoke_v2 \
  --contention-dir results/contention/smoke_v2 \
  --study-name smoke_v2 \
  --output-root /tmp/smoke-v2-recheck
```

The second command writes three CSVs and three PNGs to a separate output directory. PNG rendering may vary with Matplotlib and font versions. The analysis and collection scripts were not changed for this archive.

The next collection stage is [formal-v1](formal-experiment-protocol.md): ten trials per condition in the existing blocked-randomized schedule, split into two sessions. These five rehearsal trials do not count toward that schedule.
