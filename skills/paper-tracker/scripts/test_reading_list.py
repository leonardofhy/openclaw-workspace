#!/usr/bin/env python3
"""Unit tests for reading_list.py."""

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

import reading_list

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

SAMPLE_ARXIV_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2301.07041v1</id>
        <title>  Attention Is All You Need Revisited  </title>
        <summary>  We propose a new architecture based on attention mechanisms.  </summary>
        <published>2023-01-17T00:00:00Z</published>
        <author><name>Alice Smith</name></author>
        <author><name>Bob Jones</name></author>
        <category term="cs.CL"/>
        <category term="cs.LG"/>
        <link href="http://arxiv.org/pdf/2301.07041v1" title="pdf"/>
      </entry>
    </feed>
""")

SAMPLE_TRACKED_PAPERS = [
    {
        "id": "P-001",
        "title": "Test Paper One",
        "authors": ["Smith", "Johnson"],
        "arxiv_id": "2301.07041",
        "url": "https://arxiv.org/abs/2301.07041",
        "status": "queued"
    },
    {
        "id": "P-002",
        "title": "Another Test Paper",
        "authors": ["Wilson"],
        "arxiv_id": "2302.12345",
        "url": "https://arxiv.org/abs/2302.12345",
        "status": "read"
    }
]

SAMPLE_READING_QUEUE = [
    {
        "id": "R-001",
        "paper_id": "P-001",
        "title": "Test Paper One",
        "authors": ["Smith", "Johnson"],
        "arxiv_id": "2301.07041",
        "url": "https://arxiv.org/abs/2301.07041",
        "priority": "high",
        "status": "queued",
        "notes": [],
        "added_at": "2026-03-19T10:00:00+08:00",
        "updated_at": "2026-03-19T10:00:00+08:00"
    },
    {
        "id": "R-002",
        "paper_id": "",
        "title": "Direct arXiv Addition",
        "authors": ["Brown"],
        "arxiv_id": "2303.99999",
        "url": "https://arxiv.org/abs/2303.99999",
        "priority": "medium",
        "status": "reading",
        "notes": [{"text": "Interesting approach", "time": "2026-03-19T11:00:00+08:00", "type": "note"}],
        "added_at": "2026-03-19T09:00:00+08:00",
        "updated_at": "2026-03-19T11:00:00+08:00"
    }
]

# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestReadingList(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

        # Patch workspace detection
        self.workspace_patcher = patch.object(reading_list, 'WORKSPACE', self.workspace)
        self.workspace_patcher.start()

        # Update paths
        reading_list.READING_QUEUE_PATH = self.workspace / "memory" / "papers" / "reading-queue.json"
        reading_list.PAPERS_JSONL_PATH = self.workspace / "memory" / "papers" / "papers.jsonl"

    def tearDown(self):
        """Clean up test fixtures."""
        self.workspace_patcher.stop()
        self.temp_dir.cleanup()

    def create_reading_queue(self, queue: list = None):
        """Create a test reading queue file."""
        if queue is None:
            queue = SAMPLE_READING_QUEUE.copy()
        queue_path = reading_list.READING_QUEUE_PATH
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        queue_path.write_text(json.dumps(queue, ensure_ascii=False))

    def create_papers_jsonl(self, papers: list = None):
        """Create a test papers.jsonl file."""
        if papers is None:
            papers = SAMPLE_TRACKED_PAPERS.copy()
        papers_path = reading_list.PAPERS_JSONL_PATH
        papers_path.parent.mkdir(parents=True, exist_ok=True)
        with open(papers_path, "w") as f:
            for paper in papers:
                f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    def test_load_reading_queue(self):
        """Test loading reading queue."""
        self.create_reading_queue()
        queue = reading_list.load_reading_queue()
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue[0]["id"], "R-001")
        self.assertEqual(queue[1]["status"], "reading")

    def test_load_reading_queue_no_file(self):
        """Test loading reading queue when file doesn't exist."""
        queue = reading_list.load_reading_queue()
        self.assertEqual(len(queue), 0)

    def test_next_queue_id(self):
        """Test queue ID generation."""
        # Empty queue
        self.assertEqual(reading_list.next_queue_id([]), "R-001")

        # Existing items
        queue = [{"id": "R-001"}, {"id": "R-003"}]
        self.assertEqual(reading_list.next_queue_id(queue), "R-004")

    def test_find_queue_item(self):
        """Test finding queue items."""
        queue = SAMPLE_READING_QUEUE.copy()

        item = reading_list.find_queue_item(queue, "R-001")
        self.assertIsNotNone(item)
        self.assertEqual(item["title"], "Test Paper One")

        item = reading_list.find_queue_item(queue, "R-999")
        self.assertIsNone(item)

    def test_update_queue_item(self):
        """Test updating queue items."""
        queue = SAMPLE_READING_QUEUE.copy()

        item = reading_list.update_queue_item(queue, "R-001", {"status": "reading"})
        self.assertIsNotNone(item)
        self.assertEqual(item["status"], "reading")
        self.assertIn("updated_at", item)

        item = reading_list.update_queue_item(queue, "R-999", {"status": "done"})
        self.assertIsNone(item)

    def test_load_tracked_papers(self):
        """Test loading tracked papers."""
        self.create_papers_jsonl()
        papers = reading_list.load_tracked_papers()
        self.assertEqual(len(papers), 2)
        self.assertEqual(papers[0]["id"], "P-001")

    def test_find_tracked_paper(self):
        """Test finding tracked papers."""
        self.create_papers_jsonl()

        paper = reading_list.find_tracked_paper("P-001")
        self.assertIsNotNone(paper)
        self.assertEqual(paper["title"], "Test Paper One")

        paper = reading_list.find_tracked_paper("P-999")
        self.assertIsNone(paper)

    def test_parse_arxiv_id(self):
        """Test arXiv ID parsing."""
        # Bare ID
        self.assertEqual(reading_list.parse_arxiv_id("2301.07041"), "2301.07041")

        # URL formats
        self.assertEqual(reading_list.parse_arxiv_id("https://arxiv.org/abs/2301.07041"), "2301.07041")
        self.assertEqual(reading_list.parse_arxiv_id("arxiv.org/pdf/2301.07041v1"), "2301.07041v1")

        # Invalid input
        self.assertIsNone(reading_list.parse_arxiv_id("not-an-arxiv-id"))

    @patch('urllib.request.urlopen')
    def test_fetch_arxiv_metadata(self, mock_urlopen):
        """Test fetching arXiv metadata."""
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.read.return_value = SAMPLE_ARXIV_XML.encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        metadata = reading_list.fetch_arxiv_metadata("2301.07041")

        self.assertEqual(metadata["title"], "Attention Is All You Need Revisited")
        self.assertEqual(metadata["authors"], ["Alice Smith", "Bob Jones"])
        self.assertEqual(metadata["arxiv_id"], "2301.07041")
        self.assertEqual(metadata["date"], "2023-01-17")

    def test_cmd_add_from_tracker(self):
        """Test adding paper from tracker."""
        self.create_papers_jsonl()
        self.create_reading_queue([])  # Empty queue

        args = MagicMock()
        args.from_tracker = "P-001"
        args.source = None
        args.priority = "high"
        args.note = "Must read"

        result = reading_list.cmd_add(args)
        self.assertEqual(result, 0)

        # Check that item was added
        queue = reading_list.load_reading_queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["paper_id"], "P-001")
        self.assertEqual(queue[0]["priority"], "high")
        self.assertEqual(len(queue[0]["notes"]), 1)

    def test_cmd_add_from_tracker_duplicate(self):
        """Test adding duplicate paper from tracker."""
        self.create_papers_jsonl()
        self.create_reading_queue()  # Has R-001 with paper_id P-001

        args = MagicMock()
        args.from_tracker = "P-001"
        args.source = None
        args.priority = None
        args.note = None

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reading_list.cmd_add(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("already in reading queue", output)

    def test_cmd_add_from_tracker_not_found(self):
        """Test adding non-existent paper from tracker."""
        self.create_papers_jsonl()

        args = MagicMock()
        args.from_tracker = "P-999"
        args.source = None

        result = reading_list.cmd_add(args)
        self.assertEqual(result, 1)

    @patch('reading_list.fetch_arxiv_metadata')
    def test_cmd_add_by_arxiv_id(self, mock_fetch):
        """Test adding paper by arXiv ID."""
        mock_fetch.return_value = {
            "title": "New Paper Title",
            "authors": ["New Author"],
            "arxiv_id": "2304.12345",
            "url": "https://arxiv.org/abs/2304.12345",
            "date": "2023-04-01",
            "categories": ["cs.LG"]
        }

        self.create_reading_queue([])  # Empty queue

        args = MagicMock()
        args.from_tracker = None
        args.source = "2304.12345"
        args.priority = "medium"
        args.note = None

        result = reading_list.cmd_add(args)
        self.assertEqual(result, 0)

        # Check that item was added
        queue = reading_list.load_reading_queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["arxiv_id"], "2304.12345")
        self.assertEqual(queue[0]["title"], "New Paper Title")

    def test_cmd_add_invalid_arxiv(self):
        """Test adding invalid arXiv ID."""
        args = MagicMock()
        args.from_tracker = None
        args.source = "invalid-id"
        args.priority = None
        args.note = None

        result = reading_list.cmd_add(args)
        self.assertEqual(result, 1)

    def test_cmd_list_basic(self):
        """Test basic listing."""
        self.create_reading_queue()

        args = MagicMock()
        args.status = None
        args.limit = None

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reading_list.cmd_list(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("R-001", output)
        self.assertIn("R-002", output)
        self.assertIn("Test Paper One", output)

    def test_cmd_list_with_status_filter(self):
        """Test listing with status filter."""
        self.create_reading_queue()

        args = MagicMock()
        args.status = "reading"
        args.limit = None

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reading_list.cmd_list(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertNotIn("R-001", output)  # queued
        self.assertIn("R-002", output)     # reading

    def test_cmd_show(self):
        """Test showing queue item details."""
        self.create_reading_queue()

        args = MagicMock()
        args.id = "R-002"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reading_list.cmd_show(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Direct arXiv Addition", output)
        self.assertIn("reading", output)
        self.assertIn("Brown", output)
        self.assertIn("Interesting approach", output)

    def test_cmd_show_not_found(self):
        """Test showing non-existent item."""
        self.create_reading_queue()

        args = MagicMock()
        args.id = "R-999"

        result = reading_list.cmd_show(args)
        self.assertEqual(result, 1)

    def test_cmd_done(self):
        """Test marking paper as done."""
        self.create_reading_queue()

        args = MagicMock()
        args.id = "R-001"
        args.note = "Finished reading, great insights"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reading_list.cmd_done(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Marked R-001 as done", output)

        # Verify status was updated
        queue = reading_list.load_reading_queue()
        item = reading_list.find_queue_item(queue, "R-001")
        self.assertEqual(item["status"], "done")
        self.assertEqual(len(item["notes"]), 1)
        self.assertEqual(item["notes"][0]["type"], "done")

    def test_cmd_skip(self):
        """Test marking paper as skipped."""
        self.create_reading_queue()

        args = MagicMock()
        args.id = "R-001"
        args.reason = "Not relevant to current research"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reading_list.cmd_skip(args)

        self.assertEqual(result, 0)

        # Verify status was updated
        queue = reading_list.load_reading_queue()
        item = reading_list.find_queue_item(queue, "R-001")
        self.assertEqual(item["status"], "skipped")
        self.assertIn("Not relevant", item["notes"][0]["text"])

    def test_cmd_priority(self):
        """Test updating priority."""
        self.create_reading_queue()

        args = MagicMock()
        args.id = "R-002"
        args.new_priority = "high"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reading_list.cmd_priority(args)

        self.assertEqual(result, 0)

        # Verify priority was updated
        queue = reading_list.load_reading_queue()
        item = reading_list.find_queue_item(queue, "R-002")
        self.assertEqual(item["priority"], "high")

    def test_cmd_note(self):
        """Test adding a note."""
        self.create_reading_queue()

        args = MagicMock()
        args.id = "R-001"
        args.text = "This is a test note"

        result = reading_list.cmd_note(args)
        self.assertEqual(result, 0)

        # Verify note was added
        queue = reading_list.load_reading_queue()
        item = reading_list.find_queue_item(queue, "R-001")
        self.assertEqual(len(item["notes"]), 1)
        self.assertEqual(item["notes"][0]["text"], "This is a test note")

    def test_cmd_stats(self):
        """Test statistics display."""
        self.create_reading_queue()

        args = MagicMock()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reading_list.cmd_stats(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Total items: 2", output)
        self.assertIn("queued: 1", output)
        self.assertIn("reading: 1", output)

    def test_cmd_export_json(self):
        """Test JSON export."""
        self.create_reading_queue()

        args = MagicMock()
        args.format = "json"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reading_list.cmd_export(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()

        # Should be valid JSON
        exported_data = json.loads(output)
        self.assertEqual(len(exported_data), 2)

    def test_cmd_export_markdown(self):
        """Test Markdown export."""
        self.create_reading_queue()

        args = MagicMock()
        args.format = "md"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = reading_list.cmd_export(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("# Reading Queue", output)
        self.assertIn("## ⏳ Queued", output)
        self.assertIn("## 📖 Reading", output)
        self.assertIn("Test Paper One", output)

# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()