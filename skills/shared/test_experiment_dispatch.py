#!/usr/bin/env python3
"""Tests for skills/shared/experiment_dispatch.py

Covers:
- dry-run dispatch (no SSH/SCP needed)
- slurm template generation
- result parsing / JSONL append
- run_cmd / ssh_cmd with mocked subprocess

Usage:
    python3 -m pytest skills/shared/test_experiment_dispatch.py -v
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_dispatch as ed


class TestRunCmd(unittest.TestCase):
    """run_cmd() — dry-run vs real execution."""

    def test_dry_run_returns_empty_string(self):
        result = ed.run_cmd(["echo", "hello"], dry_run=True)
        self.assertEqual(result, "")

    def test_dry_run_prints_command(self, ):
        import io
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ed.run_cmd(["ssh", "host", "ls"], dry_run=True)
            self.assertIn("[DRY RUN]", mock_out.getvalue())
            self.assertIn("ssh host ls", mock_out.getvalue())

    @patch("experiment_dispatch.subprocess.run")
    def test_real_run_calls_subprocess(self, mock_run):
        mock_run.return_value = MagicMock(stdout="output\n", returncode=0)
        result = ed.run_cmd(["echo", "hi"])
        mock_run.assert_called_once()
        self.assertEqual(result, "output")

    @patch("experiment_dispatch.subprocess.run")
    def test_real_run_raises_on_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        with self.assertRaises(subprocess.CalledProcessError):
            ed.run_cmd(["false"])


class TestSshCmd(unittest.TestCase):
    """ssh_cmd() delegates to run_cmd."""

    def test_dry_run(self):
        result = ed.ssh_cmd("ls -la", dry_run=True)
        self.assertEqual(result, "")

    @patch("experiment_dispatch.subprocess.run")
    def test_real_ssh(self, mock_run):
        mock_run.return_value = MagicMock(stdout="files\n", returncode=0)
        result = ed.ssh_cmd("ls -la")
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd, ["ssh", "battleship", "ls -la"])


class TestScpTo(unittest.TestCase):

    def test_dry_run(self):
        result = ed.scp_to("/tmp/x.py", "~/experiments/x.py", dry_run=True)
        self.assertEqual(result, "")

    @patch("experiment_dispatch.subprocess.run")
    def test_real_scp(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        ed.scp_to("/tmp/x.py", "~/experiments/x.py")
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "scp")
        self.assertIn("battleship:~/experiments/x.py", cmd)


class TestAppendJsonl(unittest.TestCase):

    def test_creates_file_and_appends(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sub" / "log.jsonl"
            record = {"job_id": "123", "status": "ok"}
            ed.append_jsonl(path, record)
            self.assertTrue(path.exists())
            lines = path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]), record)

    def test_appends_multiple_records(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "log.jsonl"
            ed.append_jsonl(path, {"a": 1})
            ed.append_jsonl(path, {"b": 2})
            lines = path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 2)


MOCK_TEMPLATE = """\
#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition={partition}
#SBATCH --gres=gpu:{gpu_count}
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={memory}
#SBATCH --time={walltime}
conda activate {conda_env}
python {script_basename} --model {model} --output-dir {remote_output_dir} {extra_args}
LOG_DIR={log_dir}
"""


class TestGenerateSlurmScript(unittest.TestCase):
    """generate_slurm_script() produces valid sbatch content."""

    def _gen(self, **kwargs):
        defaults = dict(job_name="test_exp", model="whisper-base", script_basename="run.py")
        defaults.update(kwargs)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(MOCK_TEMPLATE)
            tmp_path = Path(f.name)
        try:
            with patch.object(ed, "TEMPLATE_PATH", tmp_path):
                return ed.generate_slurm_script(**defaults)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_contains_job_name(self):
        self.assertIn("#SBATCH --job-name=test_exp", self._gen())

    def test_contains_model(self):
        self.assertIn("whisper-small", self._gen(model="whisper-small"))

    def test_contains_script_basename(self):
        self.assertIn("train_model.py", self._gen(script_basename="train_model.py"))

    def test_overrides_gpu_count(self):
        self.assertIn("gpu:2", self._gen(gpu_count="2"))

    def test_overrides_walltime(self):
        self.assertIn("08:00:00", self._gen(walltime="08:00:00"))

    def test_default_partition(self):
        self.assertIn("--partition=gpu", self._gen())


class TestCmdDispatchDryRun(unittest.TestCase):
    """cmd_dispatch() with --dry-run should not execute SSH/SCP."""

    def test_dry_run_does_not_ssh(self):
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"# test script\n")
            script_path = f.name

        try:
            args = argparse.Namespace(
                script=script_path,
                model="whisper-base",
                name="test_job",
                gpus=1,
                walltime="04:00:00",
                mem="32G",
                dry_run=True,
            )
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as tf:
                tf.write(MOCK_TEMPLATE)
                tmp_tmpl = Path(tf.name)
            try:
                with patch.object(ed, "TEMPLATE_PATH", tmp_tmpl):
                    ed.cmd_dispatch(args)
            finally:
                tmp_tmpl.unlink(missing_ok=True)
        finally:
            os.unlink(script_path)

    def test_dry_run_invalid_model_exits(self):
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"# test\n")
            script_path = f.name
        try:
            args = argparse.Namespace(
                script=script_path,
                model="whisper-xxl",
                name="bad",
                gpus=1,
                walltime="04:00:00",
                mem="32G",
                dry_run=True,
            )
            with self.assertRaises(SystemExit):
                ed.cmd_dispatch(args)
        finally:
            os.unlink(script_path)

    def test_dry_run_missing_script_exits(self):
        args = argparse.Namespace(
            script="/nonexistent/path.py",
            model="whisper-base",
            name="bad",
            gpus=1,
            walltime="04:00:00",
            mem="32G",
            dry_run=True,
        )
        with self.assertRaises(SystemExit):
            ed.cmd_dispatch(args)


class TestValidModels(unittest.TestCase):

    def test_valid_models_tuple(self):
        self.assertIn("whisper-base", ed.VALID_MODELS)
        self.assertIn("whisper-small", ed.VALID_MODELS)
        self.assertIn("whisper-medium", ed.VALID_MODELS)
        self.assertNotIn("whisper-large", ed.VALID_MODELS)


class TestSlurmDefaults(unittest.TestCase):

    def test_defaults_contain_required_keys(self):
        for key in ("partition", "gpu_count", "cpus", "memory", "walltime", "conda_env"):
            self.assertIn(key, ed.SLURM_DEFAULTS)


if __name__ == "__main__":
    unittest.main()
