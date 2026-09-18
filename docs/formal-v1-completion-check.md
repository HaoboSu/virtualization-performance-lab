# Formal-v1 completion check

Date: 2026-09-18

This is the final repository-level QA record for the completed Formal-v1 experiment.

## Archive integrity

- VM1 raw benchmark inventory: **50/50** expected TXT files.
- VM2 paired contention inventory: **40/40** expected TXT files.
- Expected load/run identities are complete: 10 matched blocks at 0%, 25%, 50%, 75%, and 100%.
- The full blocked-randomized schedule contains **50 trials**.
- No extra TXT files are present inside the two analyzed Formal-v1 raw-data directories.

## Analysis and outputs

- Dedicated final analyzer: `analysis/analyze_formal_v1.py`.
- Dependency file includes NumPy, pandas, SciPy, and Matplotlib.
- Final processed outputs include the run-level results, coverage checks, descriptive summary, repeated-measures tests, sensitivity analysis, outlier record, matched-run slopes, and direction-consistency table.
- Final Formal-v1 figures are stored under `figures/formal_v1/`.
- Final interpretation and limitations are documented in [formal-v1-results.md](formal-v1-results.md).

## Documentation QA

- README reports Formal-v1 as **50/50 completed and validated**.
- Session-1 documentation is explicitly marked as a historical checkpoint rather than current project status.
- The formal protocol is explicitly marked as completed and retained for provenance.
- Relative Markdown links across repository documentation were checked; no broken internal relative links were found in the final QA pass.
- Pilot and smoke artifacts remain separate from the final Formal-v1 dataset.

## Reproduction

From the repository root:

```bash
python3 -m pip install -r requirements.txt
python3 analysis/analyze_formal_v1.py
```

The final analyzer validates the accepted inventory and pairing before regenerating outputs.

## Freeze decision

Formal-v1 is considered **complete and frozen**. Future host telemetry, custom latency benchmarks, other hypervisors, additional repetitions, or memory/storage/network interference experiments are extensions and should be versioned as new studies rather than modifying the completed Formal-v1 dataset.
