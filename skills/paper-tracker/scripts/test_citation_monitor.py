#!/usr/bin/env python3
"""Unit tests for citation_monitor.py."""

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

import citation_monitor

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

SAMPLE_KNOWLEDGE_GRAPH = textwrap.dedent("""\
    # Knowledge Graph

    ## Research Papers

    - **Glazer et al. "Beyond Transcription" (2025, aiOla)** — [arXiv:2508.15882]
      - KEY METHODS: Encoder Lens (novel), saturation layer
    - **Mariotte et al. "Sparse Autoencoders Make Audio Foundation Models more Explainable"** [arXiv:2509.24793]
    - **AudioSAE (Aparin et al., 2026, EACL)** — SAE on all 12 layers [arXiv:2602.05027]
      - KEY FINDINGS: >50% feature stability across seeds
""")

SAMPLE_S2_CITATIONS_RESPONSE = {
    "data": [
        {
            "citingPaper": {
                "paperId": "cite1",
                "title": "Follow-up work on transcription",
                "authors": [{"name": "Johnson"}],
                "year": 2026,
                "url": "https://example.com/cite1",
                "externalIds": {"ArXiv": "2601.12345"}
            }
        },
        {
            "citingPaper": {
                "paperId": "cite2",
                "title": "Another citation",
                "authors": [{"name": "Wilson"}, {"name": "Davis"}],
                "year": 2025,
                "url": "https://example.com/cite2",
                "externalIds": {}
            }
        }
    ]
}

SAMPLE_S2_TRENDING_RESPONSE = {
    "data": [
        {
            "paperId": "trend1",
            "title": "Trending Speech Paper",
            "authors": [{"name": "Brown"}, {"name": "Taylor"}],
            "year": 2026,
            "citationCount": 50,
            "url": "https://example.com/trend1",
            "externalIds": {"ArXiv": "2602.99999"}
        },
        {
            "paperId": "trend2",
            "title": "Another Trending Paper",
            "authors": [{"name": "White"}],
            "year": 2025,
            "citationCount": 30,
            "url": "https://example.com/trend2",
            "externalIds": {}
        }
    ]
}

# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestCitationMonitor(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

        # Patch workspace detection
        self.workspace_patcher = patch.object(citation_monitor, 'WORKSPACE', self.workspace)
        self.workspace_patcher.start()

        # Update paths
        citation_monitor.STATE_PATH = self.workspace / "memory" / "papers" / "citation-state.json"
        citation_monitor.KNOWLEDGE_GRAPH_PATH = self.workspace / "memory" / "learning" / "knowledge-graph.md"

    def tearDown(self):
        """Clean up test fixtures."""
        self.workspace_patcher.stop()
        self.temp_dir.cleanup()

    def create_knowledge_graph(self, content: str = SAMPLE_KNOWLEDGE_GRAPH):
        """Create a test knowledge graph file."""
        kg_path = citation_monitor.KNOWLEDGE_GRAPH_PATH
        kg_path.parent.mkdir(parents=True, exist_ok=True)
        kg_path.write_text(content)

    def create_citation_state(self, state: dict):
        """Create a test citation state file."""
        state_path = citation_monitor.STATE_PATH
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state))

    def test_extract_arxiv_papers(self):
        """Test extracting arXiv papers from knowledge graph."""
        self.create_knowledge_graph()

        papers = citation_monitor.extract_arxiv_papers()

        self.assertEqual(len(papers), 3)
        self.assertEqual(papers[0]["arxiv_id"], "2508.15882")
        self.assertEqual(papers[1]["arxiv_id"], "2509.24793")
        self.assertEqual(papers[2]["arxiv_id"], "2602.05027")

        # Check title extraction
        self.assertIn("Beyond Transcription", papers[0]["title"])
        self.assertIn("Sparse Autoencoders", papers[1]["title"])

    def test_extract_arxiv_papers_no_file(self):
        """Test handling missing knowledge graph."""
        papers = citation_monitor.extract_arxiv_papers()
        self.assertEqual(len(papers), 0)

    def test_load_citation_state(self):
        """Test loading citation state."""
        test_state = {
            "last_check": "2026-03-19",
            "known_citations": {"2508.15882": ["cite1", "cite2"]},
            "known_author_papers": {}
        }
        self.create_citation_state(test_state)

        state = citation_monitor.load_state()
        self.assertEqual(state["last_check"], "2026-03-19")
        self.assertEqual(len(state["known_citations"]["2508.15882"]), 2)

    def test_load_citation_state_no_file(self):
        """Test loading citation state when file doesn't exist."""
        state = citation_monitor.load_state()
        self.assertIsNone(state["last_check"])
        self.assertEqual(state["known_citations"], {})

    @patch('citation_monitor.s2_get')
    def test_check_citations(self, mock_s2_get):
        """Test checking citations for a paper."""
        mock_s2_get.return_value = SAMPLE_S2_CITATIONS_RESPONSE

        citations = citation_monitor.check_citations("2508.15882")

        self.assertEqual(len(citations), 2)
        self.assertEqual(citations[0]["title"], "Follow-up work on transcription")
        self.assertEqual(citations[0]["arxiv_id"], "2601.12345")
        self.assertEqual(citations[1]["arxiv_id"], "")  # No arXiv ID

    @patch('citation_monitor.s2_get')
    def test_check_citations_with_since_filter(self, mock_s2_get):
        """Test checking citations with year filter."""
        mock_s2_get.return_value = SAMPLE_S2_CITATIONS_RESPONSE

        citations = citation_monitor.check_citations("2508.15882", since="2026-01-01")

        # Should only return 2026 citation
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["year"], 2026)

    @patch('citation_monitor.s2_get')
    def test_check_citations_api_error(self, mock_s2_get):
        """Test handling API errors."""
        mock_s2_get.return_value = None

        citations = citation_monitor.check_citations("2508.15882")
        self.assertEqual(len(citations), 0)

    @patch('citation_monitor.s2_get')
    def test_fetch_trending_papers(self, mock_s2_get):
        """Test fetching trending papers."""
        mock_s2_get.return_value = SAMPLE_S2_TRENDING_RESPONSE

        papers = citation_monitor.fetch_trending_papers("speech interpretability", 5)

        self.assertEqual(len(papers), 2)
        self.assertEqual(papers[0]["title"], "Trending Speech Paper")
        self.assertIn("trending_score", papers[0])

    @patch('citation_monitor.check_citations')
    @patch('citation_monitor.extract_arxiv_papers')
    def test_cmd_check_basic(self, mock_extract, mock_check_citations):
        """Test basic citation checking command."""
        # Setup mocks
        mock_extract.return_value = [
            {"arxiv_id": "2508.15882", "title": "Test Paper", "authors": ["Smith"]}
        ]
        mock_check_citations.return_value = [
            {"s2_id": "new_cite", "title": "New Citation", "authors": ["Johnson"], "year": 2026}
        ]

        # Mock args
        args = MagicMock()
        args.since = None
        args.authors = None

        # Capture output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = citation_monitor.cmd_check(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Found 1 arXiv papers", output)
        self.assertIn("new citation", output.lower())

    @patch('citation_monitor.extract_arxiv_papers')
    def test_cmd_check_author_filter(self, mock_extract):
        """Test citation checking with author filter."""
        mock_extract.return_value = [
            {"arxiv_id": "2508.15882", "title": "Test Paper", "authors": ["Smith", "Johnson"]},
            {"arxiv_id": "2509.24793", "title": "Other Paper", "authors": ["Wilson"]}
        ]

        args = MagicMock()
        args.since = None
        args.authors = "Smith,Johnson"

        with patch('citation_monitor.check_citations', return_value=[]), \
             patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            citation_monitor.cmd_check(args)

        output = mock_stdout.getvalue()
        self.assertIn("Filtering papers by authors", output)
        self.assertIn("Filtered to 1 papers", output)

    def test_cmd_report_no_data(self):
        """Test report command with no data."""
        args = MagicMock()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = citation_monitor.cmd_report(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("No checks have been run yet", output)

    def test_cmd_report_with_data(self):
        """Test report command with existing data."""
        test_state = {
            "last_check": "2026-03-19",
            "known_citations": {"2508.15882": ["cite1", "cite2"]},
            "known_author_papers": {"Smith": ["paper1"]}
        }
        self.create_citation_state(test_state)

        args = MagicMock()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = citation_monitor.cmd_report(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Last check: 2026-03-19", output)
        self.assertIn("Total known citations: 2", output)

    @patch('citation_monitor.fetch_trending_papers')
    def test_cmd_trending(self, mock_fetch):
        """Test trending papers command."""
        mock_fetch.return_value = [
            {
                "title": "Trending Paper",
                "authors": [{"name": "Smith"}],
                "year": 2026,
                "citationCount": 50,
                "trending_score": 45.0,
                "externalIds": {"ArXiv": "2602.99999"}
            }
        ]

        args = MagicMock()
        args.query = "test query"
        args.limit = 5

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = citation_monitor.cmd_trending(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Trending Paper", output)
        self.assertIn("arXiv:2602.99999", output)

    def test_cmd_reset(self):
        """Test reset command."""
        # Create some initial state
        test_state = {"last_check": "2026-03-19", "known_citations": {"test": ["cite1"]}}
        self.create_citation_state(test_state)

        args = MagicMock()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = citation_monitor.cmd_reset(args)

        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Citation state reset", output)

        # Verify state was reset
        new_state = citation_monitor.load_state()
        self.assertIsNone(new_state["last_check"])
        self.assertEqual(new_state["known_citations"], {})

    def test_s2_paper_id(self):
        """Test Semantic Scholar paper ID generation."""
        self.assertEqual(citation_monitor.s2_paper_id("2508.15882"), "ARXIV:2508.15882")

# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()