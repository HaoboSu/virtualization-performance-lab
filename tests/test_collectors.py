"""Exercise collector success/failure handling with fake executables, not load tests."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'scripts').mkdir()
        self.bin = self.root/'bin'
        self.bin.mkdir()
        for name in ('run_benchmark.sh', 'run_contention.sh'):
            shutil.copy2(ROOT/'scripts'/name, self.root/'scripts'/name)
        self.executable('timedatectl', '#!/bin/sh\necho yes\n')
        self.executable('sysbench', '''#!/bin/sh
if [ "$1" = "--version" ]; then echo 'sysbench 1.0.20'; exit 0; fi
case "$*" in
  *--time=5*) [ "${FAKE_FAIL:-}" = warmup ] && exit 7 ;;
  *--time=30*) [ "${FAKE_FAIL:-}" = measurement ] && exit 7 ;;
esac
echo 'TEST FIXTURE: no real benchmark was run'
exit 0
''')
        self.executable('stress-ng', '''#!/bin/sh
if [ "$1" = "--version" ]; then echo 'stress-ng, version 0.17.06'; exit 0; fi
printf '%s\n' "$@" > "$FAKE_ARGS"
echo 'TEST FIXTURE: no real stress load was run'
exit "${FAKE_STRESS_EXIT:-0}"
''')
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ['PATH'], FAKE_ARGS=str(self.root/'args'))

    def executable(self, name, text):
        path = self.bin/name
        path.write_text(text)
        path.chmod(0o755)

    def run_script(self, name, load, **env):
        return subprocess.run(['bash', str(self.root/'scripts'/name), str(load), '1', 'fixture'],
                              env=dict(self.env, **env), capture_output=True, text=True)

    def test_benchmark_completion_and_overwrite_refusal(self):
        result = self.run_script('run_benchmark.sh', 0)
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.root/'results/raw/fixture/baseline_run_1.txt'
        before = path.read_bytes()
        text = before.decode()
        for label in ('collection_protocol: cpu_fixed_v1', 'warmup_started_at:', 'warmup_finished_at:',
                      'clock_synchronized: yes', 'exit_status: 0'):
            self.assertIn(label, text)
        self.assertFalse(Path(str(path)+'.tmp').exists())
        self.assertNotEqual(self.run_script('run_benchmark.sh', 0).returncode, 0)
        self.assertEqual(path.read_bytes(), before)

    def test_warmup_failure_preserves_incomplete_log(self):
        result = self.run_script('run_benchmark.sh', 25, FAKE_FAIL='warmup')
        self.assertNotEqual(result.returncode, 0)
        path = self.root/'results/raw/fixture/contention_25_run_1.txt'
        self.assertFalse(path.exists())
        self.assertNotIn('exit_status: 0', Path(str(path)+'.tmp').read_text())

    def test_measurement_failure_preserves_incomplete_log(self):
        result = self.run_script('run_benchmark.sh', 25, FAKE_FAIL='measurement')
        self.assertNotEqual(result.returncode, 0)
        path = self.root/'results/raw/fixture/contention_25_run_1.txt'
        self.assertFalse(path.exists())
        self.assertNotIn('exit_status: 0', Path(str(path)+'.tmp').read_text())

    def test_contention_defaults_and_completion(self):
        result = self.run_script('run_contention.sh', 25)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = (self.root/'args').read_text().splitlines()
        for option, value in [('--cpu', '2'), ('--cpu-load', '25'), ('--cpu-method', 'int64'), ('--timeout', '120s')]:
            self.assertEqual(args[args.index(option)+1], value)
        path = self.root/'results/contention/fixture/contention_25_run_1.txt'
        text = path.read_text()
        for label in ('cpu_workers: 2', 'cpu_method: int64', 'contention_duration_seconds: 120', 'exit_status: 0'):
            self.assertIn(label, text)
        self.assertNotEqual(self.run_script('run_contention.sh', 25).returncode, 0)
        self.assertEqual(path.read_text(), text)

    def test_contention_failure_preserves_incomplete_log(self):
        result = self.run_script('run_contention.sh', 25, FAKE_STRESS_EXIT='7')
        self.assertNotEqual(result.returncode, 0)
        path = self.root/'results/contention/fixture/contention_25_run_1.txt'
        self.assertFalse(path.exists())
        self.assertNotIn('exit_status: 0', Path(str(path)+'.tmp').read_text())


if __name__ == '__main__':
    unittest.main()
