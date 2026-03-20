#!/usr/bin/env python3
"""Unit tests for hf_research CLI."""

import json
import os
import sys
import tempfile
import unittest
import urllib.error
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Bootstrap: point at the scripts dir and stub out shared.jsonl_store
# so we can import hf_research without a real workspace.
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).parent))

# Provide a minimal JsonlStore that can be monkey-patched per test
class _FakeJsonlStore:
    """In-memory JsonlStore stand-in."""

    def __init__(self, rel_path: str = "", prefix: str = "ID"):
        self.prefix = prefix
        self._items: list[dict] = []
        self.path = Path(tempfile.mktemp(suffix=".jsonl"))

    def load(self) -> list[dict]:
        return list(self._items)

    def next_id(self, items=None) -> str:
        items = items if items is not None else self._items
        if not items:
            return f"{self.prefix}-001"
        nums = []
        for it in items:
            try:
                nums.append(int(it["id"].split("-")[1]))
            except (KeyError, IndexError, ValueError):
                pass
        return f"{self.prefix}-{(max(nums) + 1):03d}" if nums else f"{self.prefix}-001"

    def append(self, item: dict) -> dict:
        if "id" not in item:
            item["id"] = self.next_id()
        self._items.append(item)
        return item

    def update(self, item_id: str, updates: dict) -> dict | None:
        for it in self._items:
            if it.get("id") == item_id:
                it.update(updates)
                return it
        return None

    def find(self, item_id: str) -> dict | None:
        for it in self._items:
            if it.get("id") == item_id:
                return it
        return None

    def filter(self, **kwargs) -> list[dict]:
        result = list(self._items)
        for k, v in kwargs.items():
            result = [i for i in result if i.get(k) == v]
        return result


# Stub the shared module before importing hf_research
_fake_shared = type(sys)("shared")
_fake_shared_jsonl = type(sys)("shared.jsonl_store")
_fake_shared_jsonl.JsonlStore = _FakeJsonlStore
_fake_shared.jsonl_store = _fake_shared_jsonl
sys.modules.setdefault("shared", _fake_shared)
sys.modules.setdefault("shared.jsonl_store", _fake_shared_jsonl)

import importlib
import hf_research
importlib.reload(hf_research)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stores(test_case):
    """Replace module-level stores with fresh fake stores."""
    push = _FakeJsonlStore(prefix="HFP")
    exp = _FakeJsonlStore(prefix="EXP")
    test_case._push_store = push
    test_case._exp_store = exp
    hf_research.push_store = push
    hf_research.exp_store = exp


def _add_exp(store, exp_id="EXP-001", name="test-exp", **kwargs):
    item = {"id": exp_id, "name": name, "status": "success", "hf_repo": None}
    item.update(kwargs)
    store._items.append(item)
    return item


def _ok_proc(**kwargs):
    p = MagicMock()
    p.returncode = 0
    p.stdout = kwargs.get("stdout", "")
    p.stderr = ""
    return p


def _fail_proc(stderr="upload failed"):
    p = MagicMock()
    p.returncode = 1
    p.stdout = ""
    p.stderr = stderr
    return p


# ---------------------------------------------------------------------------
# Test: upload
# ---------------------------------------------------------------------------

class TestUpload(unittest.TestCase):

    def setUp(self):
        _make_stores(self)
        self.tmpdir = tempfile.mkdtemp()
        # Create a dummy checkpoint dir
        self.ckpt = Path(self.tmpdir) / "checkpoint-1000"
        self.ckpt.mkdir()
        (self.ckpt / "config.json").write_text("{}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("hf_research.run_hf", return_value=_ok_proc())
    def test_upload_success(self, mock_hf):
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["upload", "--repo", "user/model", "--path", str(self.ckpt)])
        self.assertEqual(rc, 0)
        self.assertIn("user/model", out.getvalue())
        mock_hf.assert_called_once()
        # push logged
        pushes = self._push_store.load()
        self.assertEqual(len(pushes), 1)
        self.assertEqual(pushes[0]["repo"], "user/model")

    @patch("hf_research.run_hf", return_value=_ok_proc())
    def test_upload_with_exp_link(self, mock_hf):
        _add_exp(self._exp_store, "EXP-001")
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["upload", "--repo", "user/model",
                                   "--path", str(self.ckpt), "--exp", "EXP-001"])
        self.assertEqual(rc, 0)
        exp = self._exp_store.find("EXP-001")
        self.assertEqual(exp["hf_repo"], "user/model")
        push = self._push_store.load()[0]
        self.assertEqual(push["exp_id"], "EXP-001")

    @patch("hf_research.run_hf", return_value=_ok_proc())
    def test_upload_with_exp_not_found_warns(self, mock_hf):
        err = StringIO()
        with patch("sys.stderr", err):
            rc = hf_research.main(["upload", "--repo", "user/model",
                                   "--path", str(self.ckpt), "--exp", "EXP-999"])
        self.assertEqual(rc, 0)  # still succeeds
        self.assertIn("EXP-999", err.getvalue())

    @patch("hf_research.run_hf", return_value=_fail_proc("network error"))
    def test_upload_hf_failure(self, mock_hf):
        err = StringIO()
        with patch("sys.stderr", err):
            rc = hf_research.main(["upload", "--repo", "user/model", "--path", str(self.ckpt)])
        self.assertEqual(rc, 1)
        self.assertIn("failed", err.getvalue())
        self.assertEqual(len(self._push_store.load()), 0)

    def test_upload_missing_path(self):
        err = StringIO()
        with patch("sys.stderr", err):
            rc = hf_research.main(["upload", "--repo", "user/model", "--path", "/nonexistent/path"])
        self.assertEqual(rc, 1)

    @patch("hf_research.run_hf", return_value=_ok_proc())
    def test_upload_commit_msg_forwarded(self, mock_hf):
        with patch("sys.stdout", StringIO()):
            hf_research.main(["upload", "--repo", "user/model",
                               "--path", str(self.ckpt),
                               "--commit-msg", "step 1000"])
        call_args = mock_hf.call_args[0]
        self.assertIn("--commit-message", call_args)
        self.assertIn("step 1000", call_args)

    @patch("hf_research.run_hf", return_value=_ok_proc())
    def test_upload_private_flag(self, mock_hf):
        with patch("sys.stdout", StringIO()):
            hf_research.main(["upload", "--repo", "user/model",
                               "--path", str(self.ckpt), "--private"])
        call_args = mock_hf.call_args[0]
        self.assertIn("--private", call_args)


# ---------------------------------------------------------------------------
# Test: download
# ---------------------------------------------------------------------------

class TestDownload(unittest.TestCase):

    def setUp(self):
        _make_stores(self)

    @patch("hf_research.run_hf", return_value=_ok_proc(stdout="Downloaded to ./models"))
    def test_download_success(self, mock_hf):
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["download", "--repo", "openai/whisper-base"])
        self.assertEqual(rc, 0)
        self.assertIn("openai/whisper-base", out.getvalue())

    @patch("hf_research.run_hf", return_value=_ok_proc())
    def test_download_with_out(self, mock_hf):
        with patch("sys.stdout", StringIO()):
            rc = hf_research.main(["download", "--repo", "openai/whisper-base", "--out", "./models"])
        self.assertEqual(rc, 0)
        call_args = mock_hf.call_args[0]
        self.assertIn("--local-dir", call_args)
        self.assertIn("./models", call_args)

    @patch("hf_research.run_hf", return_value=_ok_proc())
    def test_download_dataset_type(self, mock_hf):
        with patch("sys.stdout", StringIO()):
            rc = hf_research.main(["download", "--repo", "mozilla/cv13", "--type", "dataset"])
        self.assertEqual(rc, 0)
        call_args = mock_hf.call_args[0]
        self.assertIn("--repo-type", call_args)
        self.assertIn("dataset", call_args)

    @patch("hf_research.run_hf", return_value=_fail_proc("not found"))
    def test_download_failure(self, mock_hf):
        err = StringIO()
        with patch("sys.stderr", err):
            rc = hf_research.main(["download", "--repo", "user/nonexistent"])
        self.assertEqual(rc, 1)


# ---------------------------------------------------------------------------
# Test: search
# ---------------------------------------------------------------------------

MOCK_MODEL_RESULTS = [
    {
        "id": "openai/whisper-base",
        "modelId": "openai/whisper-base",
        "pipeline_tag": "automatic-speech-recognition",
        "downloads": 1000000,
        "likes": 500,
        "tags": ["speech", "asr", "whisper"],
    },
    {
        "id": "openai/whisper-large-v3",
        "modelId": "openai/whisper-large-v3",
        "pipeline_tag": "automatic-speech-recognition",
        "downloads": 500000,
        "likes": 300,
        "tags": ["speech", "asr"],
    },
]

MOCK_DATASET_RESULTS = [
    {
        "id": "mozilla-foundation/common_voice_13_0",
        "downloads": 50000,
        "likes": 100,
        "tags": ["speech", "multilingual"],
    }
]


class TestSearch(unittest.TestCase):

    def setUp(self):
        _make_stores(self)

    @patch("hf_research.hf_api_get", return_value=MOCK_MODEL_RESULTS)
    def test_search_models(self, mock_api):
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["search", "whisper"])
        self.assertEqual(rc, 0)
        output = out.getvalue()
        self.assertIn("openai/whisper-base", output)
        self.assertIn("automatic-speech-recognition", output)

    @patch("hf_research.hf_api_get", return_value=MOCK_DATASET_RESULTS)
    def test_search_datasets(self, mock_api):
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["search", "common voice", "--type", "dataset"])
        self.assertEqual(rc, 0)
        self.assertIn("mozilla-foundation", out.getvalue())
        # API should be called with datasets endpoint
        call_path = mock_api.call_args[0][0]
        self.assertIn("datasets", call_path)

    @patch("hf_research.hf_api_get", return_value=[])
    def test_search_no_results(self, mock_api):
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["search", "zzz-nonexistent-xyz"])
        self.assertEqual(rc, 0)
        self.assertIn("No", out.getvalue())

    @patch("hf_research.hf_api_get", side_effect=Exception("network error"))
    def test_search_api_failure(self, mock_api):
        err = StringIO()
        with patch("sys.stderr", err):
            rc = hf_research.main(["search", "whisper"])
        self.assertEqual(rc, 1)

    @patch("hf_research.hf_api_get", return_value=MOCK_MODEL_RESULTS)
    def test_search_task_filter(self, mock_api):
        with patch("sys.stdout", StringIO()):
            hf_research.main(["search", "whisper", "--task", "automatic-speech-recognition"])
        call_path = mock_api.call_args[0][0]
        self.assertIn("pipeline_tag", call_path)

    @patch("hf_research.hf_api_get", return_value=MOCK_MODEL_RESULTS[:1])
    def test_search_limit(self, mock_api):
        with patch("sys.stdout", StringIO()):
            hf_research.main(["search", "whisper", "--limit", "1"])
        call_path = mock_api.call_args[0][0]
        self.assertIn("limit=1", call_path)


# ---------------------------------------------------------------------------
# Test: status
# ---------------------------------------------------------------------------

MOCK_MODEL_INFO = {
    "id": "openai/whisper-base",
    "modelId": "openai/whisper-base",
    "author": "openai",
    "private": False,
    "downloads": 1000000,
    "likes": 500,
    "tags": ["speech", "asr", "whisper"],
    "lastModified": "2023-09-01T00:00:00.000Z",
}

MOCK_SPACE_INFO = {
    "id": "gradio/hello_world",
    "author": "gradio",
    "private": False,
    "downloads": 0,
    "likes": 100,
    "tags": [],
    "lastModified": "2024-01-01T00:00:00.000Z",
    "runtime": {
        "stage": "RUNNING",
        "hardware": {"current": "cpu-basic"},
    },
}


class TestStatus(unittest.TestCase):

    def setUp(self):
        _make_stores(self)

    @patch("hf_research.hf_api_get", return_value=MOCK_MODEL_INFO)
    def test_status_model(self, mock_api):
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["status", "openai/whisper-base"])
        self.assertEqual(rc, 0)
        output = out.getvalue()
        self.assertIn("openai/whisper-base", output)
        self.assertIn("openai", output)
        self.assertIn("1000000", output)

    @patch("hf_research.hf_api_get", return_value=MOCK_SPACE_INFO)
    def test_status_space(self, mock_api):
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["status", "gradio/hello_world", "--type", "space"])
        self.assertEqual(rc, 0)
        output = out.getvalue()
        self.assertIn("RUNNING", output)
        self.assertIn("cpu-basic", output)
        # API called with spaces endpoint
        call_path = mock_api.call_args[0][0]
        self.assertIn("spaces", call_path)

    def test_status_not_found(self):
        err_404 = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
        with patch("hf_research.hf_api_get", side_effect=err_404):
            err = StringIO()
            with patch("sys.stderr", err):
                rc = hf_research.main(["status", "user/nonexistent"])
        self.assertEqual(rc, 1)
        self.assertIn("not found", err.getvalue())


# ---------------------------------------------------------------------------
# Test: push-exp
# ---------------------------------------------------------------------------

class TestPushExp(unittest.TestCase):

    def setUp(self):
        _make_stores(self)
        self.tmpdir = tempfile.mkdtemp()
        self.ckpt = Path(self.tmpdir) / "best"
        self.ckpt.mkdir()
        (self.ckpt / "model.bin").write_bytes(b"\x00" * 16)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("hf_research.run_hf", return_value=_ok_proc())
    def test_push_exp_with_checkpoint(self, mock_hf):
        _add_exp(self._exp_store, "EXP-001", name="whisper SFT")
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["push-exp", "EXP-001",
                                   "--repo", "user/whisper-sft",
                                   "--checkpoint", str(self.ckpt),
                                   "--note", "best WER 8.3%"])
        self.assertEqual(rc, 0)
        # push logged
        pushes = self._push_store.load()
        self.assertEqual(len(pushes), 1)
        self.assertEqual(pushes[0]["exp_id"], "EXP-001")
        self.assertEqual(pushes[0]["repo"], "user/whisper-sft")
        # exp backlinked
        exp = self._exp_store.find("EXP-001")
        self.assertEqual(exp["hf_repo"], "user/whisper-sft")

    def test_push_exp_not_found(self):
        err = StringIO()
        with patch("sys.stderr", err):
            rc = hf_research.main(["push-exp", "EXP-999", "--repo", "user/model"])
        self.assertEqual(rc, 1)
        self.assertIn("EXP-999", err.getvalue())

    def test_push_exp_missing_checkpoint(self):
        _add_exp(self._exp_store, "EXP-001")
        err = StringIO()
        with patch("sys.stderr", err):
            rc = hf_research.main(["push-exp", "EXP-001",
                                   "--repo", "user/model",
                                   "--checkpoint", "/nonexistent/ckpt"])
        self.assertEqual(rc, 1)

    @patch("hf_research.run_hf", return_value=_fail_proc("auth error"))
    def test_push_exp_upload_failure(self, mock_hf):
        _add_exp(self._exp_store, "EXP-001")
        err = StringIO()
        with patch("sys.stderr", err):
            rc = hf_research.main(["push-exp", "EXP-001",
                                   "--repo", "user/model",
                                   "--checkpoint", str(self.ckpt)])
        self.assertEqual(rc, 1)
        self.assertEqual(len(self._push_store.load()), 0)

    def test_push_exp_no_checkpoint(self):
        """push-exp without --checkpoint: just links the repo, no hf CLI call."""
        _add_exp(self._exp_store, "EXP-001")
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["push-exp", "EXP-001",
                                   "--repo", "user/model",
                                   "--note", "manual link"])
        self.assertEqual(rc, 0)
        pushes = self._push_store.load()
        self.assertEqual(len(pushes), 1)
        self.assertEqual(pushes[0]["note"], "manual link")

    @patch("hf_research.run_hf", return_value=_ok_proc())
    def test_push_exp_commit_msg_includes_exp_id(self, mock_hf):
        _add_exp(self._exp_store, "EXP-002")
        with patch("sys.stdout", StringIO()):
            hf_research.main(["push-exp", "EXP-002",
                               "--repo", "user/model",
                               "--checkpoint", str(self.ckpt)])
        call_args = mock_hf.call_args[0]
        commit_msg = call_args[call_args.index("--commit-message") + 1]
        self.assertIn("EXP-002", commit_msg)


# ---------------------------------------------------------------------------
# Test: log
# ---------------------------------------------------------------------------

class TestLog(unittest.TestCase):

    def setUp(self):
        _make_stores(self)

    def _seed_pushes(self):
        for i, (repo, exp) in enumerate([
            ("user/modelA", "EXP-001"),
            ("user/modelB", "EXP-002"),
            ("user/modelC", None),
        ], 1):
            self._push_store.append({
                "repo": repo, "type": "model", "local_path": "",
                "commit_msg": "", "exp_id": exp, "note": f"push {i}",
                "pushed_at": f"2026-03-{i:02d}T10:00:00+08:00",
            })

    def test_log_empty(self):
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["log"])
        self.assertEqual(rc, 0)
        self.assertIn("No pushes", out.getvalue())

    def test_log_all(self):
        self._seed_pushes()
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["log"])
        self.assertEqual(rc, 0)
        output = out.getvalue()
        self.assertIn("user/modelA", output)
        self.assertIn("user/modelB", output)
        self.assertIn("user/modelC", output)

    def test_log_filter_exp(self):
        self._seed_pushes()
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["log", "--exp", "EXP-001"])
        self.assertEqual(rc, 0)
        output = out.getvalue()
        self.assertIn("user/modelA", output)
        self.assertNotIn("user/modelB", output)

    def test_log_limit(self):
        self._seed_pushes()
        out = StringIO()
        with patch("sys.stdout", out):
            rc = hf_research.main(["log", "--limit", "1"])
        self.assertEqual(rc, 0)
        # Only last push visible
        self.assertIn("user/modelC", out.getvalue())
        self.assertNotIn("user/modelA", out.getvalue())


# ---------------------------------------------------------------------------
# Test: CLI edge cases
# ---------------------------------------------------------------------------

class TestCliEdgeCases(unittest.TestCase):

    def test_no_command(self):
        rc = hf_research.main([])
        self.assertEqual(rc, 1)

    def test_push_store_id_format(self):
        store = _FakeJsonlStore(prefix="HFP")
        store.append({"repo": "a/b"})
        store.append({"repo": "c/d"})
        self.assertEqual(store._items[0]["id"], "HFP-001")
        self.assertEqual(store._items[1]["id"], "HFP-002")
        self.assertEqual(store.next_id(), "HFP-003")


if __name__ == "__main__":
    unittest.main()
