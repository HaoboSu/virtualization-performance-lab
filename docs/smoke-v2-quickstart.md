# Smoke-v2 rehearsal

Use the updated scripts on both VMs. This rehearsal exercises all five configured load levels under the settings intended for formal-v1. Each condition has one trial, so SD/CV are unavailable. Keep the study name `smoke_v2`; these results do not count toward the formal schedule.

## Prepare

- Host: VMware Workstation 17.6.1 build-24319023; Windows 10 build 19045.6456; Balanced power plan; AC power. Keep any separate power-mode slider setting unchanged and record it.
- VM1: `benchmark-vm`, 1 vCPU, 2 GB RAM. VM2: `contention-vm`, 2 vCPU, 2 GB RAM. Confirm these allocations in VM settings.
- Let both VMs settle for at least five minutes. Finish package installation, downloads and synchronization before collection.
- Run `timedatectl status` on both VMs. Confirm synchronized clocks and active NTP.
- On VM2, run `pgrep -a stress-ng`. No output means no process matched. If a load is still active, let it finish and investigate before proceeding.
- Work from the repository root in both terminals. Keep previous smoke-v1 files intact.

## Trial order

| Order | Configured load | VM2 command | VM1 command |
| --- | --- | --- | --- |
| 1 | 0% | Keep VM2 on and idle | `./scripts/run_benchmark.sh 0 1 smoke_v2` |
| 2 | 25% | `./scripts/run_contention.sh 25 1 smoke_v2` | `./scripts/run_benchmark.sh 25 1 smoke_v2` |
| 3 | 50% | `./scripts/run_contention.sh 50 1 smoke_v2` | `./scripts/run_benchmark.sh 50 1 smoke_v2` |
| 4 | 75% | `./scripts/run_contention.sh 75 1 smoke_v2` | `./scripts/run_benchmark.sh 75 1 smoke_v2` |
| 5 | 100% | `./scripts/run_contention.sh 100 1 smoke_v2` | `./scripts/run_benchmark.sh 100 1 smoke_v2` |

For every nonzero load, start VM2 first. After its `started_at` appears, wait 10 seconds, then run the matching VM1 command. Wait for both scripts to finish. Wait at least 10 seconds after the load ends before the next trial. After the baseline, also allow at least 10 seconds before continuing.

Default settings: VM2 uses two `int64` workers for 120 seconds. VM1 warms up for 5 seconds and measures for 30 seconds with one thread. Do not set duration or worker overrides during this rehearsal.

## Check and analyze

Preserve VM1's five logs in `results/raw/smoke_v2/` and VM2's four logs in `results/contention/smoke_v2/`. Copy both directories to the same analysis machine without changing their contents.

```bash
python3 analysis/analyze_results.py \
  --raw-dir results/raw/smoke_v2 \
  --contention-dir results/contention/smoke_v2 \
  --validate-only
```

This checks available records only. Also confirm the inventory is five VM1 logs and four VM2 logs, one trial at each planned load. Review any failure before repeating a trial. Keep rejected attempts outside the analyzed directories, with a written reason.

After validation, generate summaries in a separate output directory:

```bash
python3 analysis/analyze_results.py \
  --raw-dir results/raw/smoke_v2 \
  --contention-dir results/contention/smoke_v2 \
  --output-root /tmp/smoke-v2-analysis
```

Outputs include a per-trial coverage CSV. `NA` in SD/CV columns and absent error bars are expected with one run per condition. A successful rehearsal confirms the workflow; the [formal experiment](formal-experiment-protocol.md) supplies repeated observations in randomized order.
