#!/usr/bin/env python3
"""Unit tests for paper tracker CLI."""

import json
import os
import sys
import tempfile
import textwrap
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure the scripts directory is importable
sys.path.insert(0, str(Path(__file__).parent))
import papers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ARXIV_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2301.07041v1</id>
        <title>  Attention Is All You Need
          (revisited)  </title>
        <summary>  We propose a new architecture based on attention.
          It achieves state-of-the-art results.  </summary>
        <published>2023-01-17T00:00:00Z</published>
        <author><name>Alice Smith</name></author>
        <author><name>Bob Jones</name></author>
        <category term="cs.CL"/>
        <category term="cs.AI"/>
        <link title="pdf" href="http://arxiv.org/pdf/2301.07041v1" rel="related" type="application/pdf"/>
      </entry>
    </feed>
""")

SAMPLE_ARXIV_ERROR_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/api/errors#Error</id>
        <title></title>
        <summary>Error</summary>
      </entry>
    </feed>
""")


class PaperTestBase(unittest.TestCase):
    """Base class that sets up a temp JSONL store for each test."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store_path = Path(self.tmpdir) / "papers.jsonl"
        # Monkey-patch store to use temp path
        papers.store.path = self.store_path
        papers.STORE_PATH = self.store_path

    def tearDown(self):
        if self.store_path.exists():
            self.store_path.unlink()
        os.rmdir(self.tmpdir)

    def _add_sample_paper(self, paper_id="P-001", **overrides):
        """Helper to insert a paper directly into the store."""
        paper = {
            "id": paper_id,
            "title": "Test Paper Title",
            "authors": ["Author A", "Author B"],
            "abstract": "This is an abstract about speech recognition.",
            "arxiv_id": "2301.07041",
            "url": "https://arxiv.org/abs/2301.07041",
            "pdf_url": "",
            "date": "2023-01-17",
            "categories": ["cs.CL"],
            "venue": "",
            "status": "queued",
            "tags": [],
            "notes": [],
            "added_at": "2026-03-18T10:00:00+08:00",
            "updated_at": "2026-03-18T10:00:00+08:00",
        }
        paper.update(overrides)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "a") as f:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")
        return paper


# ---------------------------------------------------------------------------
# Test: Arxiv ID parsing
# ---------------------------------------------------------------------------

class TestArxivIdParsing(unittest.TestCase):
    def test_bare_id(self):
        self.assertEqual(papers.parse_arxiv_id("2301.07041"), "2301.07041")

    def test_bare_id_with_version(self):
        self.assertEqual(papers.parse_arxiv_id("2301.07041v2"), "2301.07041v2")

    def test_abs_url(self):
        self.assertEqual(papers.parse_arxiv_id("https://arxiv.org/abs/2301.07041"), "2301.07041")

    def test_pdf_url(self):
        self.assertEqual(papers.parse_arxiv_id("https://arxiv.org/pdf/2301.07041v1"), "2301.07041v1")

    def test_http_url(self):
        self.assertEqual(papers.parse_arxiv_id("http://arxiv.org/abs/2301.07041"), "2301.07041")

    def test_invalid(self):
        self.assertIsNone(papers.parse_arxiv_id("not-an-id"))

    def test_empty(self):
        self.assertIsNone(papers.parse_arxiv_id(""))

    def test_five_digit_id(self):
        self.assertEqual(papers.parse_arxiv_id("2301.12345"), "2301.12345")


# ---------------------------------------------------------------------------
# Test: Add command
# ---------------------------------------------------------------------------

class TestAddCommand(PaperTestBase):

    @patch("papers.fetch_arxiv_metadata")
    def test_add_arxiv(self, mock_fetch):
        mock_fetch.return_value = {
            "title": "Attention Is All You Need",
            "authors": ["Alice Smith", "Bob Jones"],
            "abstract": "We propose a new architecture.",
            "arxiv_id": "2301.07041",
            "url": "https://arxiv.org/abs/2301.07041",
            "pdf_url": "http://arxiv.org/pdf/2301.07041v1",
            "date": "2023-01-17",
            "categories": ["cs.CL", "cs.AI"],
        }
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["add", "2301.07041"])
        self.assertEqual(ret, 0)
        self.assertIn("P-001", out.getvalue())
        items = papers.store.load()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Attention Is All You Need")
        self.assertEqual(items[0]["status"], "queued")

    @patch("papers.fetch_arxiv_metadata")
    def test_add_duplicate_arxiv(self, mock_fetch):
        """Adding the same arxiv paper twice should not duplicate."""
        self._add_sample_paper()
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["add", "2301.07041"])
        self.assertEqual(ret, 0)
        self.assertIn("already tracked", out.getvalue())
        self.assertEqual(len(papers.store.load()), 1)
        mock_fetch.assert_not_called()

    def test_add_manual(self):
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main([
                "add", "--manual",
                "--title", "Manual Paper",
                "--authors", "Author X, Author Y",
                "--venue", "ICASSP 2026",
            ])
        self.assertEqual(ret, 0)
        items = papers.store.load()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Manual Paper")
        self.assertEqual(items[0]["venue"], "ICASSP 2026")
        self.assertEqual(items[0]["authors"], ["Author X", "Author Y"])

    def test_add_manual_no_title(self):
        err = StringIO()
        with patch("sys.stderr", err):
            ret = papers.main(["add", "--manual"])
        self.assertEqual(ret, 1)

    def test_add_invalid_arxiv_id(self):
        err = StringIO()
        with patch("sys.stderr", err):
            ret = papers.main(["add", "not-a-valid-id"])
        self.assertEqual(ret, 1)


# ---------------------------------------------------------------------------
# Test: List command
# ---------------------------------------------------------------------------

class TestListCommand(PaperTestBase):

    def test_list_empty(self):
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["list"])
        self.assertEqual(ret, 0)
        self.assertIn("No papers", out.getvalue())

    def test_list_all(self):
        self._add_sample_paper("P-001", title="Paper Alpha")
        self._add_sample_paper("P-002", title="Paper Beta", status="reading")
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["list"])
        self.assertEqual(ret, 0)
        self.assertIn("Paper Alpha", out.getvalue())
        self.assertIn("Paper Beta", out.getvalue())
        self.assertIn("2 paper(s)", out.getvalue())

    def test_list_filter_status(self):
        self._add_sample_paper("P-001", status="queued")
        self._add_sample_paper("P-002", status="reading")
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["list", "--status", "reading"])
        self.assertEqual(ret, 0)
        self.assertIn("P-002", out.getvalue())
        self.assertNotIn("P-001", out.getvalue())

    def test_list_filter_tag(self):
        self._add_sample_paper("P-001", tags=["speech"])
        self._add_sample_paper("P-002", tags=["vision"])
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["list", "--tag", "speech"])
        self.assertEqual(ret, 0)
        self.assertIn("P-001", out.getvalue())
        self.assertNotIn("P-002", out.getvalue())

    def test_list_limit(self):
        for i in range(5):
            self._add_sample_paper(f"P-{i+1:03d}", title=f"Paper {i+1}")
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["list", "--limit", "2"])
        self.assertEqual(ret, 0)
        self.assertIn("2 paper(s)", out.getvalue())


# ---------------------------------------------------------------------------
# Test: Show command
# ---------------------------------------------------------------------------

class TestShowCommand(PaperTestBase):

    def test_show(self):
        self._add_sample_paper("P-001", notes=[{"text": "Great paper", "time": "2026-03-18T10:00:00+08:00"}])
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["show", "P-001"])
        self.assertEqual(ret, 0)
        output = out.getvalue()
        self.assertIn("Test Paper Title", output)
        self.assertIn("Author A", output)
        self.assertIn("Great paper", output)

    def test_show_not_found(self):
        err = StringIO()
        with patch("sys.stderr", err):
            ret = papers.main(["show", "P-999"])
        self.assertEqual(ret, 1)


# ---------------------------------------------------------------------------
# Test: Tag command
# ---------------------------------------------------------------------------

class TestTagCommand(PaperTestBase):

    def test_tag_add(self):
        self._add_sample_paper("P-001")
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["tag", "P-001", "speech", "ssl"])
        self.assertEqual(ret, 0)
        paper = papers.store.find("P-001")
        self.assertEqual(sorted(paper["tags"]), ["speech", "ssl"])

    def test_tag_idempotent(self):
        """Adding same tag twice should not duplicate."""
        self._add_sample_paper("P-001", tags=["speech"])
        papers.main(["tag", "P-001", "speech", "new-tag"])
        paper = papers.store.find("P-001")
        self.assertEqual(paper["tags"].count("speech"), 1)
        self.assertIn("new-tag", paper["tags"])

    def test_tag_not_found(self):
        err = StringIO()
        with patch("sys.stderr", err):
            ret = papers.main(["tag", "P-999", "test"])
        self.assertEqual(ret, 1)


# ---------------------------------------------------------------------------
# Test: Status command
# ---------------------------------------------------------------------------

class TestStatusCommand(PaperTestBase):

    def test_status_update(self):
        self._add_sample_paper("P-001", status="queued")
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["status", "P-001", "reading"])
        self.assertEqual(ret, 0)
        paper = papers.store.find("P-001")
        self.assertEqual(paper["status"], "reading")

    def test_status_invalid(self):
        self._add_sample_paper("P-001")
        err = StringIO()
        with patch("sys.stderr", err):
            ret = papers.main(["status", "P-001", "invalid"])
        self.assertEqual(ret, 1)

    def test_status_not_found(self):
        err = StringIO()
        with patch("sys.stderr", err):
            ret = papers.main(["status", "P-999", "read"])
        self.assertEqual(ret, 1)


# ---------------------------------------------------------------------------
# Test: Note command
# ---------------------------------------------------------------------------

class TestNoteCommand(PaperTestBase):

    def test_add_note(self):
        self._add_sample_paper("P-001")
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["note", "P-001", "Key insight about attention"])
        self.assertEqual(ret, 0)
        paper = papers.store.find("P-001")
        self.assertEqual(len(paper["notes"]), 1)
        self.assertEqual(paper["notes"][0]["text"], "Key insight about attention")

    def test_add_multiple_notes(self):
        self._add_sample_paper("P-001")
        papers.main(["note", "P-001", "Note 1"])
        papers.main(["note", "P-001", "Note 2"])
        paper = papers.store.find("P-001")
        self.assertEqual(len(paper["notes"]), 2)

    def test_note_not_found(self):
        err = StringIO()
        with patch("sys.stderr", err):
            ret = papers.main(["note", "P-999", "test"])
        self.assertEqual(ret, 1)

    def test_note_cjk(self):
        """CJK characters in notes should work."""
        self._add_sample_paper("P-001")
        papers.main(["note", "P-001", "這篇 paper 的 attention 很有趣"])
        paper = papers.store.find("P-001")
        self.assertIn("attention 很有趣", paper["notes"][0]["text"])


# ---------------------------------------------------------------------------
# Test: Search command
# ---------------------------------------------------------------------------

class TestSearchCommand(PaperTestBase):

    def test_search_by_title(self):
        self._add_sample_paper("P-001", title="Whisper ASR Model")
        self._add_sample_paper("P-002", title="Vision Transformer")
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["search", "whisper"])
        self.assertEqual(ret, 0)
        self.assertIn("P-001", out.getvalue())
        self.assertNotIn("P-002", out.getvalue())

    def test_search_by_abstract(self):
        self._add_sample_paper("P-001", abstract="We study mechanistic interpretability.")
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["search", "mechanistic"])
        self.assertIn("P-001", out.getvalue())

    def test_search_by_tag(self):
        self._add_sample_paper("P-001", tags=["mech-interp"])
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["search", "mech-interp"])
        self.assertIn("P-001", out.getvalue())

    def test_search_by_notes(self):
        self._add_sample_paper("P-001", notes=[{"text": "layer 3 important", "time": ""}])
        out = StringIO()
        with patch("sys.stdout", out):
            papers.main(["search", "layer 3"])
        self.assertIn("P-001", out.getvalue())

    def test_search_no_results(self):
        self._add_sample_paper("P-001")
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["search", "nonexistent-query-xyz"])
        self.assertEqual(ret, 0)
        self.assertIn("No papers", out.getvalue())

    def test_search_cjk(self):
        self._add_sample_paper("P-001", title="語音辨識模型研究")
        out = StringIO()
        with patch("sys.stdout", out):
            papers.main(["search", "語音辨識"])
        self.assertIn("P-001", out.getvalue())

    def test_search_multi_token(self):
        """Multi-word query: all tokens must appear."""
        self._add_sample_paper("P-001", title="Attention Mechanism in Speech", abstract="")
        self._add_sample_paper("P-002", title="Attention in Vision", abstract="")
        out = StringIO()
        with patch("sys.stdout", out):
            papers.main(["search", "attention speech"])
        self.assertIn("P-001", out.getvalue())
        self.assertNotIn("P-002", out.getvalue())


# ---------------------------------------------------------------------------
# Test: Stats command
# ---------------------------------------------------------------------------

class TestStatsCommand(PaperTestBase):

    def test_stats_empty(self):
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["stats"])
        self.assertEqual(ret, 0)
        self.assertIn("No papers", out.getvalue())

    def test_stats_with_data(self):
        self._add_sample_paper("P-001", status="queued", tags=["speech"])
        self._add_sample_paper("P-002", status="reading", tags=["speech", "ssl"])
        self._add_sample_paper("P-003", status="read", tags=["vision"])
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["stats"])
        self.assertEqual(ret, 0)
        output = out.getvalue()
        self.assertIn("Total papers: 3", output)
        self.assertIn("queued: 1", output)
        self.assertIn("reading: 1", output)
        self.assertIn("read: 1", output)
        self.assertIn("speech: 2", output)


# ---------------------------------------------------------------------------
# Test: Export command
# ---------------------------------------------------------------------------

class TestExportCommand(PaperTestBase):

    def test_export_json(self):
        self._add_sample_paper("P-001", title="Test Paper")
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["export", "--format", "json"])
        self.assertEqual(ret, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Test Paper")

    def test_export_md(self):
        self._add_sample_paper("P-001", title="Test Paper", status="reading", tags=["speech"])
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["export", "--format", "md"])
        self.assertEqual(ret, 0)
        output = out.getvalue()
        self.assertIn("# Paper Reading List", output)
        self.assertIn("Test Paper", output)
        self.assertIn("Reading", output)

    def test_export_empty(self):
        out = StringIO()
        with patch("sys.stdout", out):
            ret = papers.main(["export", "--format", "md"])
        self.assertEqual(ret, 0)
        self.assertIn("No papers", out.getvalue())


# ---------------------------------------------------------------------------
# Test: Arxiv metadata fetching
# ---------------------------------------------------------------------------

class TestArxivFetch(unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_fetch_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = SAMPLE_ARXIV_XML.encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        meta = papers.fetch_arxiv_metadata("2301.07041")
        self.assertEqual(meta["title"], "Attention Is All You Need (revisited)")
        self.assertEqual(meta["authors"], ["Alice Smith", "Bob Jones"])
        self.assertEqual(meta["date"], "2023-01-17")
        self.assertIn("cs.CL", meta["categories"])
        self.assertIn("attention", meta["abstract"].lower())

    @patch("urllib.request.urlopen")
    def test_fetch_invalid_id(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = SAMPLE_ARXIV_ERROR_XML.encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with self.assertRaises(ValueError):
            papers.fetch_arxiv_metadata("0000.00000")


# ---------------------------------------------------------------------------
# Test: Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases(PaperTestBase):

    def test_auto_increment_id(self):
        self._add_sample_paper("P-001")
        self._add_sample_paper("P-002")
        # Next auto-ID should be P-003
        next_id = papers.store.next_id()
        self.assertEqual(next_id, "P-003")

    def test_no_command(self):
        """Running with no args should print help and return 1."""
        ret = papers.main([])
        self.assertEqual(ret, 1)

    def test_malformed_jsonl_line(self):
        """Malformed lines should be skipped gracefully."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "w") as f:
            f.write('{"id": "P-001", "title": "Good"}\n')
            f.write("not valid json\n")
            f.write('{"id": "P-002", "title": "Also Good"}\n')
        items = papers.store.load()
        self.assertEqual(len(items), 2)


if __name__ == "__main__":
    unittest.main()
