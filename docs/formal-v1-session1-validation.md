# Formal-v1 session 1: data and validation

Session 1 contains **25 of the 50 planned benchmark trials**, collected on 2026-09-16: five runs at each configured neighboring-VM load of 0%, 25%, 50%, 75%, and 100%. Its 20 nonzero-load trials have matching VM2 logs. The archived files pass the current role, metadata, execution, schedule, and recorded-window checks. Session 2 is pending; this is an interim data release, not a completed formal experiment.

## Archived data

- [VM1 benchmark logs](../results/raw/formal_v1/): 25 files, including five baselines.
- [VM2 load logs](../results/contention/formal_v1/): 20 files.
- [Session-1 schedule](../experiments/formal_v1_session1_schedule.csv): the rows with `session=1` from the [unchanged full schedule](../experiments/formal_v1_schedule.csv).
- [Per-run metrics](../results/processed/formal_v1_session1_results.csv), [interim summary](../results/processed/formal_v1_session1_summary.csv), and [coverage checks](../results/processed/formal_v1_session1_coverage.csv).

All 45 raw files are byte-identical to the accepted ZIP entries. The archives passed CRC checks and exact filename-inventory checks. There are no duplicate filenames or unfinished logs in the accepted dataset. Each nonzero condition has runs 1–5 in both VM roles. VM1 throughput and P95 values agree with all 25 screenshots reviewed during collection.

Accepted source archives and SHA-256 digests:

```text
VM1: 22ffc5a8-f873-4774-a3ec-ea31171dbdc5.zip
1a01e7a1573ad91936614ae1cda7e8280117aab4c23a79165a07dca901809f8b

VM2: formal_v1 vm2.zip
e2ed817d1275f3e99c5daa61bdde5900bb7fe27db168fbe18add1e55a0495356
```

The accepted VM1 export contains only `benchmark-vm` sysbench logs; the accepted VM2 export contains only `contention-vm` stress-ng logs. An earlier mixed-role VM1 export was rejected before this archive was assembled. No values were reconstructed from screenshots or manually substituted into the raw logs.

## Recorded collection settings

All files record study `formal_v1`, protocol `cpu_fixed_v1`, repository revision `97c28ca6a3d61920e24cba6466d7555f03369b10`, synchronized-clock status `yes`, and exit status `0`.

| Setting | VM1 | VM2 |
| --- | --- | --- |
| Hostname | `benchmark-vm` | `contention-vm` |
| Guest kernel | `Linux 6.8.0-139-generic` | `Linux 6.8.0-139-generic` |
| Tool | sysbench 1.0.20 | stress-ng 0.17.06 |
| Concurrency | 1 benchmark thread | 2 CPU workers |
| Duration | 5 s warm-up, 30 s measurement | 120 s configured load |
| Workload | CPU prime-number limit 10000 | Fixed method `int64` |

The kernel differs from the recorded smoke-v2 kernel (`6.8.0-138-generic`), but is consistent throughout this session in both roles. Pilot and smoke observations are not pooled into the formal data.

Each VM2 log reports two passed workers, zero failed workers, zero untrustworthy metrics, and successful completion. Tool versions and workload settings are consistent within each VM role.

## Ordering and coverage

All times below are UTC on 2026-09-16. The first baseline warm-up begins at 01:05:51.892674481; the last benchmark ends at 03:10:13.983250732; the last load ends at 03:11:25.559659342.

Observed trial order matches blocks 1–5 of the fixed schedule:

| Block / run number | Configured VM2 load order (%) |
| --- | --- |
| 1 | 0, 25, 50, 100, 75 |
| 2 | 75, 25, 50, 0, 100 |
| 3 | 0, 75, 100, 25, 50 |
| 4 | 25, 100, 75, 50, 0 |
| 5 | 75, 100, 0, 25, 50 |

- All 20 load windows cover their paired benchmark's entire warm-up and measurement, with at least the required five seconds at both ends.
- Recorded pre-warm-up margins range from **9.228648 to 23.737548 seconds**; post-measurement margins range from **61.262577 to 75.721295 seconds**.
- None of the five baseline windows overlaps a supplied load window. No benchmark overlaps a different trial's supplied load window.
- The smallest gap from the end of one recorded trial to the start of the next is **55.439176 seconds**, exceeding the ten-second cooldown requirement.

The margins use guest wall-clock timestamps at the analyzer's microsecond precision. They do not measure the exact inter-VM clock offset, the precise instant CPU workers become active, or actual host CPU utilization. The logs do not independently establish host AC power, Windows power-mode settings, thermal state, or absence of unrecorded background activity.

### Collection annotations

For `contention_50_run_3`, the recorded pre-warm-up margin is **9.228648 seconds**. This passes the five-second minimum coverage check but is below the procedure's ten-second waiting target. Retain the observation with this annotation; subsequent collection should continue to wait a full ten seconds after VM2 prints `started_at`.

The same pair follows a **1780.169568-second** gap after the previous trial. The acquisition history around this interval, including whether the saved pair replaced an earlier attempt or either VM was restarted, still requires an operator note. The preserved pair passes the recorded-data checks; those checks do not establish a complete history of all attempts.

The 100% run-2 benchmark reports **1753.41 events/s** and **0.89 ms P95**. It passes the recorded-data checks and is retained. The lower throughput increases that condition's sample SD and CV; it is not excluded because of its performance value. No cause for the fluctuation is established by these logs.

## Interim observations

Throughput is mean ± sample SD. P95 is the arithmetic mean of the five per-run P95 values, not a percentile calculated from pooled events. Decreases use this session's five-run baseline mean as the denominator.

| Configured VM2 load | N | Throughput (events/s) | Throughput CV (%) | Throughput decrease (%) | Mean latency (ms) | Mean per-run P95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0% | 5 | 2628.33 ± 45.25 | 1.72 | 0.00 | 0.378 | 0.472 |
| 25% | 5 | 2512.31 ± 67.33 | 2.68 | 4.41 | 0.396 | 0.546 |
| 50% | 5 | 2487.77 ± 23.88 | 0.96 | 5.35 | 0.400 | 0.574 |
| 75% | 5 | 2363.51 ± 60.41 | 2.56 | 10.08 | 0.424 | 0.658 |
| 100% | 5 | 2225.12 ± 270.28 | 12.15 | 15.34 | 0.456 | 0.660 |

These descriptive observations are limited to the first session on one host. The configured load percentages describe the stress-ng setting inside VM2, not measured host utilization. No final significance, causal mechanism, or generalizable effect size is claimed. Complete session 2 under the fixed protocol before reporting the full 50-trial result.

## Reproduce the checks and CSV snapshot

From the repository root:

```bash
python3 analysis/analyze_results.py \
  --raw-dir results/raw/formal_v1 \
  --contention-dir results/contention/formal_v1 \
  --schedule experiments/formal_v1_session1_schedule.csv \
  --validate-only
```

The subset contains 25 trials; passing this command does not certify completion of the full 50-trial schedule. The original full-schedule analysis gate remains unchanged.

The following uses the existing parser, strict formal-mode pairing checks, and statistical functions to regenerate only the explicitly named session-1 CSVs. It selects runs 1–5 into a temporary workspace, so the snapshot can also be reproduced after session 2 is added. New output goes to a separate temporary directory; the repository snapshots are not overwritten.

```bash
python3 - <<'PY'
from pathlib import Path
import csv
import shutil
import sys
import tempfile

root = Path.cwd()
sys.path.insert(0, str(root / "analysis"))
from analyze_results import parse_sysbench_file, validate_trials, summarize
from analyze_results import write_per_run_csv, write_summary_csv
from log_validation import validate_log_pairs

schedule = root / "experiments/formal_v1_session1_schedule.csv"
with schedule.open(newline="") as handle:
    trials = list(csv.DictReader(handle))
work = Path(tempfile.mkdtemp(prefix="formal-v1-session1-"))
raw, load = work / "raw", work / "contention"
raw.mkdir()
load.mkdir()
for trial in trials:
    pressure, run = int(trial["load_percent"]), int(trial["run_number"])
    name = f"baseline_run_{run}.txt" if pressure == 0 else f"contention_{pressure}_run_{run}.txt"
    shutil.copyfile(root / "results/raw/formal_v1" / name, raw / name)
    if pressure:
        shutil.copyfile(root / "results/contention/formal_v1" / name, load / name)
rows = sorted((parse_sysbench_file(p) for p in raw.glob("*.txt")),
              key=lambda row: (row["pressure_percent"], row["run"]))
validate_trials(rows, schedule)
coverage = validate_log_pairs(raw, rows, load, formal=True)
out = work / "processed"
write_per_run_csv(rows, out / "formal_v1_session1_results.csv")
write_summary_csv(summarize(rows), out / "formal_v1_session1_summary.csv")
with (out / "formal_v1_session1_coverage.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(coverage[0]))
    writer.writeheader()
    writer.writerows(coverage)
print(out)
PY
```

For an independent order/cooldown check, sort the 25 trial windows by start time and compare their `(load, run)` identities with the session-1 schedule. A nonzero trial starts at its VM2 `started_at` and ends at the later of its two `finished_at` values; a baseline starts at `warmup_started_at` and ends at its VM1 `finished_at`. Subtract each preceding end from the next start to calculate the gap.

The next collection item is block 6, run 6, baseline (0%). Continue with blocks 6–10 in the original schedule and retain these session-1 snapshots as an explicitly partial release.
