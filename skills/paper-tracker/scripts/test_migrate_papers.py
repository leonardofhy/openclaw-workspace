#!/usr/bin/env python3
"""Tests for migrate_papers.py — paper reading list migration."""

import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Ensure imports resolve
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from migrate_papers import (
    infer_tags,
    parse_reading_list,
    parse_section_c_bullet,
    parse_section_c2_row,
    extract_note_summary,
    find_paper_note,
    migrate,
)

# ---------------------------------------------------------------------------
# Fixtures / sample data
# ---------------------------------------------------------------------------

SAMPLE_MD = """\
# Paper Reading List (Leo)

Last updated: 2026-02-27

## A) Quick-scan queue (Triage)
- **Smith et al. 2401.12345** (2024) — Interesting finding on transformers

## B) Deep-read queue (High priority)
- **Jones 2402.54321** (2024) — Novel speech recognition approach

## C) Completed deep reads (selected)
- **Maghsoudi & Mishra 2602.01247** (2026) — Brain-to-speech MI: compact layer-specific causal subspaces. Cycle c-20260311-1215.
- Geiger et al. — Causal Abstraction / IIT foundations
- Zhao et al. (2601.03115) — Emotion-sensitive neurons in LALMs

## C2) Deep reads completed week of Feb 26 – Mar 2 (autodidact cycles #6-#181)

| Paper | arXiv | Cycle | Key output |
|-------|-------|-------|-----------|
| Glazer "Beyond Transcription" (2025) | 2508.15882 | #6 | Encoder Lens, hallucination from residual stream |
| AudioSAE v1 (2026, EACL) | 2602.05027 | #8 | SAE all-12-layers, layer 6-7 transition |
| Sadok et al. "Codec Probe" (Interspeech 2025) | 2506.04492 | #163 | RVQ Layer 1 = semantic |

## D) Candidate paper angles
- Listen Layer Hypothesis (Track 3)
"""


# ---------------------------------------------------------------------------
# Tests: Section C bullet parsing
# ---------------------------------------------------------------------------

class TestParseSectionCBullet:
    def test_bold_with_arxiv(self):
        line = "- **Maghsoudi & Mishra 2602.01247** (2026) — Brain-to-speech MI: compact causal subspaces. Cycle c-20260311-1215."
        result = parse_section_c_bullet(line)
        assert result is not None
        assert result["arxiv_id"] == "2602.01247"
        assert "Maghsoudi" in result["title"]
        assert "Brain-to-speech" in result["description"]
        assert "20260311-1215" in result["cycle"]

    def test_no_bold_no_arxiv(self):
        line = "- Geiger et al. — Causal Abstraction / IIT foundations"
        result = parse_section_c_bullet(line)
        assert result is not None
        assert result["arxiv_id"] == ""
        assert "Geiger" in result["title"]

    def test_parenthetical_arxiv(self):
        line = "- Zhao et al. (2601.03115) — Emotion-sensitive neurons in LALMs"
        result = parse_section_c_bullet(line)
        assert result is not None
        assert result["arxiv_id"] == "2601.03115"

    def test_not_a_bullet(self):
        result = parse_section_c_bullet("Some random text")
        assert result is None

    def test_empty_line(self):
        result = parse_section_c_bullet("- ")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: Section C2 table row parsing
# ---------------------------------------------------------------------------

class TestParseSectionC2Row:
    def test_normal_row(self):
        line = '| Glazer "Beyond Transcription" (2025) | 2508.15882 | #6 | Encoder Lens, hallucination |'
        result = parse_section_c2_row(line)
        assert result is not None
        assert result["arxiv_id"] == "2508.15882"
        assert "Glazer" in result["title"]
        assert result["cycle"] == "6"
        assert "Encoder Lens" in result["description"]

    def test_header_row_skipped(self):
        result = parse_section_c2_row("| Paper | arXiv | Cycle | Key output |")
        assert result is None

    def test_separator_row_skipped(self):
        result = parse_section_c2_row("|-------|-------|-------|-----------|")
        assert result is None

    def test_non_arxiv_source(self):
        line = "| UniWhisper (2026) | (scan) | #1 | 20-task eval |"
        result = parse_section_c2_row(line)
        assert result is not None
        assert result["arxiv_id"] == ""
        assert "UniWhisper" in result["title"]


# ---------------------------------------------------------------------------
# Tests: Full markdown parsing
# ---------------------------------------------------------------------------

class TestParseReadingList:
    def test_all_sections_parsed(self):
        papers = parse_reading_list(SAMPLE_MD)
        # A: 1, B: 1, C: 3, C2: 3 = 8 total
        assert len(papers) == 8

    def test_section_a_status(self):
        papers = parse_reading_list(SAMPLE_MD)
        a_papers = [p for p in papers if p["status"] == "queued"]
        assert len(a_papers) >= 1
        assert any("Smith" in p["title"] for p in a_papers)

    def test_section_b_status(self):
        papers = parse_reading_list(SAMPLE_MD)
        b_papers = [p for p in papers if p["status"] == "reading"]
        assert len(b_papers) >= 1
        assert any("Jones" in p["title"] for p in b_papers)

    def test_section_c_status(self):
        papers = parse_reading_list(SAMPLE_MD)
        read_papers = [p for p in papers if p["status"] == "read"]
        assert len(read_papers) >= 6  # C + C2

    def test_section_d_not_parsed(self):
        """Section D (candidate angles) should NOT produce papers."""
        papers = parse_reading_list(SAMPLE_MD)
        titles = [p["title"] for p in papers]
        assert not any("Listen Layer" in t for t in titles)

    def test_empty_sections_ok(self):
        md = "## A) Quick-scan queue (Triage)\n- (empty)\n## B) Deep-read\n(empty)\n"
        papers = parse_reading_list(md)
        assert papers == []


# ---------------------------------------------------------------------------
# Tests: Tag inference
# ---------------------------------------------------------------------------

class TestInferTags:
    def test_speech_tag(self):
        tags = infer_tags("Brain-to-speech MI with audio processing")
        assert "speech" in tags

    def test_sae_tag(self):
        tags = infer_tags("Sparse Autoencoder analysis of layer 7")
        assert "sae" in tags

    def test_mech_interp_tag(self):
        tags = infer_tags("Mechanistic interpretability of attention heads")
        assert "mech-interp" in tags

    def test_multiple_tags(self):
        tags = infer_tags("SAE for speech safety evaluation benchmark")
        assert "sae" in tags
        assert "speech" in tags
        assert "safety" in tags
        assert "evaluation" in tags

    def test_no_tags(self):
        tags = infer_tags("Random unrelated text about cooking")
        assert tags == []


# ---------------------------------------------------------------------------
# Tests: Note extraction
# ---------------------------------------------------------------------------

class TestExtractNoteSummary:
    def test_extracts_content_lines(self):
        note = "# Title\n> meta\n\nFirst content line.\nSecond line.\n## Tags\ntag1"
        result = extract_note_summary(note)
        assert "First content line" in result
        assert "Second line" in result
        assert "tag1" not in result

    def test_empty_note(self):
        assert extract_note_summary("") == ""
        assert extract_note_summary("# Only a header\n> meta") == ""


# ---------------------------------------------------------------------------
# Tests: Idempotent migration
# ---------------------------------------------------------------------------

class TestMigrateIdempotent:
    def test_idempotent_skips_duplicates(self, tmp_path):
        """Running migration twice should not create duplicate entries."""
        store_path = tmp_path / "papers.jsonl"
        reading_list = tmp_path / "paper-reading-list.md"
        reading_list.write_text(SAMPLE_MD)

        with mock.patch("migrate_papers.READING_LIST", reading_list), \
             mock.patch("migrate_papers.STORE_PATH", store_path), \
             mock.patch("migrate_papers.store") as mock_store, \
             mock.patch("migrate_papers.PAPER_NOTES_DIR", tmp_path / "notes"):

            # First run: store is empty
            mock_store.load.return_value = []
            id_counter = [0]
            def fake_append(paper):
                id_counter[0] += 1
                paper["id"] = f"P-{id_counter[0]:03d}"
                return paper
            mock_store.append.side_effect = fake_append

            stats1 = migrate(dry_run=False)
            first_added = stats1["added"]
            assert first_added > 0

            # Second run: store has papers from first run
            added_papers = []
            for call in mock_store.append.call_args_list:
                added_papers.append(call[0][0])
            mock_store.load.return_value = added_papers
            mock_store.append.reset_mock()
            mock_store.append.side_effect = fake_append

            stats2 = migrate(dry_run=False)
            assert stats2["skipped"] > 0
            # Papers without arxiv IDs will still be re-added (no dedup key)
            # But those WITH arxiv IDs should be skipped
            arxiv_papers = [p for p in added_papers if p.get("arxiv_id")]
            assert stats2["skipped"] >= len(arxiv_papers)


# ---------------------------------------------------------------------------
# Tests: Note file matching
# ---------------------------------------------------------------------------

class TestFindPaperNote:
    def test_finds_matching_note(self, tmp_path):
        note_file = tmp_path / "2603.06854-audio-specialist-heads.md"
        note_file.write_text("# Note\nSome content")
        with mock.patch("migrate_papers.PAPER_NOTES_DIR", tmp_path):
            result = find_paper_note("2603.06854")
            assert result is not None
            assert "Some content" in result

    def test_no_match(self, tmp_path):
        with mock.patch("migrate_papers.PAPER_NOTES_DIR", tmp_path):
            result = find_paper_note("9999.99999")
            assert result is None

    def test_empty_arxiv_id(self):
        assert find_paper_note("") is None
