"""Regression checks; synthetic metadata exists only in temporary test folders."""

import csv
from datetime import datetime, timedelta
import io
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis import analyze_results as analysis
from analysis.log_validation import validate_log_pairs


class PairedLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.raw = self.base / 'raw'
        self.load = self.base / 'contention'
        self.raw.mkdir()
        self.load.mkdir()
        for source in (ROOT / 'results/raw/smoke_v1_checked').glob('*.txt'):
            text = source.read_text().replace('study_name: smoke_v1', 'study_name: smoke_v2')
            start = datetime.fromisoformat(re.search(r'^started_at: (.+)$', text, re.M)[1])
            text += ('\ncollection_protocol: cpu_fixed_v1\nclock_synchronized: yes\nexit_status: 0\n'
                     f'warmup_started_at: {(start-timedelta(seconds=5.1)).isoformat()}\n'
                     f'warmup_finished_at: {(start-timedelta(milliseconds=1)).isoformat()}\n')
            (self.raw / source.name).write_text(text)
        source = ROOT / 'results/contention/smoke_v1/contention_25_run_2.txt'
        text = source.read_text().replace('study_name: smoke_v1', 'study_name: smoke_v2')
        text += ('\ncollection_protocol: cpu_fixed_v1\nclock_synchronized: yes\nexit_status: 0\n'
                 'contention_duration_seconds: 120\ncpu_workers: 2\ncpu_method: int64\n')
        (self.load / source.name).write_text(text)

    def rows(self):
        return [analysis.parse_sysbench_file(path) for path in sorted(self.raw.glob('*.txt'))]

    def change(self, directory, name, old, new):
        path = directory / name
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new))

    def validate(self):
        return validate_log_pairs(self.raw, self.rows(), self.load)

    def test_valid_new_pairs(self):
        checks = self.validate()
        self.assertEqual(len(checks), 3)
        self.assertAlmostEqual(checks[-1]['load_start_margin_s'], 12.9)
        self.assertEqual(checks[-1]['load_end_margin_s'], 71)

    def test_real_smoke_first_trial_is_rejected(self):
        raw = ROOT / 'results/raw/smoke_v1'
        rows = [analysis.parse_sysbench_file(p) for p in sorted(raw.glob('*.txt'))]
        with self.assertRaisesRegex(ValueError, 'contention_25_run_1.txt: insufficient load coverage'):
            validate_log_pairs(raw, rows, ROOT / 'results/contention/smoke_v1')

    def test_real_checked_subset_passes(self):
        raw = ROOT / 'results/raw/smoke_v1_checked'
        rows = [analysis.parse_sysbench_file(p) for p in sorted(raw.glob('*.txt'))]
        self.assertEqual(len(validate_log_pairs(raw, rows, ROOT / 'results/contention/smoke_v1')), 3)

    def test_missing_pair(self):
        (self.load / 'contention_25_run_2.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'missing matching contention log'):
            self.validate()

    def test_wrong_pair_identity(self):
        self.change(self.load, 'contention_25_run_2.txt', 'run_number: 2', 'run_number: 1')
        with self.assertRaisesRegex(ValueError, 'filename disagrees'):
            self.validate()

    def test_warmup_needs_margin(self):
        self.change(self.raw, 'contention_25_run_2.txt', 'warmup_started_at: 2026-09-14T07:24:36.900000+00:00',
                    'warmup_started_at: 2026-09-14T07:24:27+00:00')
        with self.assertRaisesRegex(ValueError, 'insufficient load coverage'):
            self.validate()

    def test_non_synchronized_clock(self):
        self.change(self.load, 'contention_25_run_2.txt', 'clock_synchronized: yes', 'clock_synchronized: no')
        with self.assertRaisesRegex(ValueError, 'clock_synchronized'):
            self.validate()

    def test_wrong_method(self):
        self.change(self.load, 'contention_25_run_2.txt', 'cpu_method: int64', 'cpu_method: all')
        with self.assertRaisesRegex(ValueError, 'cpu_method'):
            self.validate()

    def test_failed_load(self):
        self.change(self.load, 'contention_25_run_2.txt', 'failed: 0', 'failed: 1')
        with self.assertRaisesRegex(ValueError, 'zero failures'):
            self.validate()

    def test_incomplete_log(self):
        (self.raw / 'baseline_run_3.txt.tmp').write_text('interrupted test fixture')
        with self.assertRaisesRegex(ValueError, 'unfinished logs'):
            self.validate()

    def test_baseline_overlapping_load(self):
        self.change(self.raw, 'baseline_run_2.txt', '07:30:', '07:24:')
        self.change(self.raw, 'baseline_run_2.txt', '07:31:', '07:25:')
        with self.assertRaisesRegex(ValueError, 'baseline overlaps'):
            self.validate()

    def cli(self, extra):
        return subprocess.run([sys.executable, str(ROOT / 'analysis/analyze_results.py'),
                               '--raw-dir', str(self.raw), '--output-root', str(self.base/'output'), *extra],
                              text=True, capture_output=True)

    def test_new_data_requires_load_logs_before_writing(self):
        result = self.cli([])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--contention-dir is required', result.stderr)
        self.assertFalse((self.base/'output').exists())

    def test_invalid_extra_file_is_not_silently_skipped(self):
        (self.raw/'baseline_run_3.txt').write_text('incomplete fixture')
        result = self.cli(['--contention-dir', str(self.load)])
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.base/'output').exists())

    def test_validate_only_writes_nothing(self):
        result = self.cli(['--contention-dir', str(self.load), '--validate-only'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.base/'output').exists())

    def test_formal_requires_schedule(self):
        result = self.cli(['--study-name', 'formal_v1', '--contention-dir', str(self.load)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires --schedule', result.stderr)

    def test_schedule_missing_trials(self):
        with self.assertRaisesRegex(ValueError, 'missing trials'):
            analysis.validate_trials(self.rows(), ROOT / 'experiments/formal_v1_schedule.csv')

    def test_singleton_na_and_unchanged_means(self):
        summaries = analysis.summarize(self.rows())
        single = summaries[1]
        self.assertTrue(math.isnan(single['throughput_sd_events_s']))
        self.assertAlmostEqual(single['throughput_degradation_vs_baseline_percent'], 15.368479070092663)
        path = self.base/'summary.csv'
        analysis.write_summary_csv(summaries, path)
        with path.open() as handle:
            last = list(csv.DictReader(handle))[-1]
        for field in ('throughput_sd_events_s', 'throughput_cv_percent', 'avg_latency_sd_ms',
                      'avg_latency_cv_percent', 'p95_latency_sd_ms', 'p95_latency_cv_percent'):
            self.assertEqual(last[field], 'NA')
        with patch('sys.stdout', new_callable=io.StringIO) as output:
            analysis.print_summary(summaries)
            self.assertIn('NA', output.getvalue())

    def test_pilot_csvs_unchanged(self):
        rows = [analysis.parse_sysbench_file(p) for p in (ROOT/'results/raw/pilot_v2').glob('*.txt')]
        rows.sort(key=lambda r: (r['pressure_percent'], r['run']))
        per_run, summary = self.base/'runs.csv', self.base/'summary.csv'
        analysis.write_per_run_csv(rows, per_run)
        analysis.write_summary_csv(analysis.summarize(rows), summary)
        self.assertEqual(per_run.read_bytes(), (ROOT/'results/processed/pilot_v2_results.csv').read_bytes())
        self.assertEqual(summary.read_bytes(), (ROOT/'results/processed/pilot_v2_summary.csv').read_bytes())


if __name__ == '__main__':
    unittest.main()
