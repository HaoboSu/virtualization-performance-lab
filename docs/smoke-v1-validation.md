# Smoke-v1 validation

The smoke test checks the two-VM collection and analysis workflow. It contains two baseline measurements and one accepted 25% measurement. These observations are preliminary and do not establish a repeatable performance effect or a formal experimental result.

## Source files and checks

Measurements were recorded on 2026-09-14. The VM exports were reviewed on 2026-09-15:

- `vm1-smoke-v1.zip`: 12 files, comprising four original benchmark logs, three checked copies, two CSVs, and three figures.
- `vm2-smoke-v1.zip`: two matching contention logs.

Both ZIP integrity checks passed. The three logs in [the checked subset](../results/raw/smoke_v1_checked/) are byte-identical to their corresponding [original logs](../results/raw/smoke_v1/). The excluded run remains in the original directory for audit. All per-run and summary CSV fields were reconciled against the raw logs and independent calculations. Running the repository's analysis script at commit `7cd0a3c` reproduced both uploaded CSVs byte-for-byte. The three uploaded figures were visually checked against those summaries.

The exported logs, CSVs, and figures are preserved without changes.

## Timing and inclusion

All times below are UTC on 2026-09-14, read from the embedded `started_at` and `finished_at` fields.

| 25% trial | VM2 load log window | VM1 benchmark log window | Decision |
| --- | --- | --- | --- |
| Run 1 | 07:18:56–07:19:56 | 07:19:29–07:19:59 | Exclude: load ended about 3 seconds before the benchmark finished. |
| Run 2 | 07:24:24–07:26:24 | 07:24:42–07:25:13 | Include for smoke analysis: the load log window covers the benchmark log window. |

The decision uses [VM2's logs](../results/contention/smoke_v1/) and timing coverage, not whether a throughput result is unusually low. Run 2 has an 18-second start margin and a 71-second end margin. Both VM2 logs report two CPU workers, zero failures, and successful completion. VM1 reports one benchmark thread, a 5-second warm-up configuration, and approximately 30 seconds of measured execution in every run.

The cross-VM comparison assumes comparable guest clocks. These ZIPs do not contain a measurement of clock offset. Script timestamps also surround metadata and command execution; they are not precise timestamps of individual stressor events. Warm-up occurs before VM1's recorded start time.

## Checked observations

| Configured VM2 load | Included runs | Mean throughput (events/s) | Mean average latency (ms) | Mean per-run P95 (ms) |
| --- | ---: | ---: | ---: | ---: |
| 0% | 2 | 2431.21 | 0.410 | 0.570 |
| 25% | 1 | 2057.57 | 0.480 | 0.740 |

Relative to the two-run baseline mean, the accepted 25% observation has **15.37% lower throughput**, **17.07% higher average latency**, and **29.82% higher P95 latency**.

The existing analysis script outputs `0.0` for sample SD and CV when `n=1`. Those entries in the 25% summary are legacy placeholders: variability is **not estimable** from a single run. The absent error bars at 25% therefore do not demonstrate zero variability. Baseline throughput sample SD is 55.15 events/s and CV is 2.27%, based on only two runs.

P95 summaries are arithmetic means of per-run P95 values, not a percentile calculated over pooled event latencies. The figure x-axis represents configured `stress-ng` load, not measured host CPU utilization. Both contention logs retain the warning about the default `all` CPU method. The second contention run used a 120-second duration; the collection script's default remains 60 seconds.

## Reproduce the checked summary

From the repository root:

```bash
python3 analysis/analyze_results.py \
  --raw-dir results/raw/smoke_v1_checked \
  --study-name smoke_v1_checked \
  --output-root /tmp/smoke-v1-recheck
```

This writes a separate recomputation. The checked copies retain `study_name: smoke_v1` in their original log metadata; `smoke_v1_checked` names the selected dataset and its analysis outputs. Analyze that subset to reproduce the reported observations. Analyzing all four original logs would include the excluded trial.

Source archive SHA-256 digests:

```text
vm1-smoke-v1.zip  52e4428b25fbcfca9b7f3847dd7037d070ae0d7727e429b7fca48865d5e3f0be
vm2-smoke-v1.zip  9c77c912f24948b83a5bb7ae3b525ce427035a8d3b054d497a704f34a8522bed
```
