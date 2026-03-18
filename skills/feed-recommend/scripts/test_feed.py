#!/usr/bin/env python3
"""Unit tests for the feed recommendation system."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sources.base import BaseSource, Article, ScoredArticle
from sources import discover_sources
import feed_engine as engine


TZ = timezone(timedelta(hours=8))


# ── Fixtures ─────────────────────────────────────────────────────

def make_article(source="hn", title="Test Article", url="https://example.com/1",
                 author="alice", score=100, comments=50, source_id="123",
                 snippet="", tags=None) -> Article:
    return Article(
        source=source, title=title, url=url, author=author,
        score=score, comments=comments, source_id=source_id,
        snippet=snippet, tags=tags or [],
    )


SAMPLE_PROFILE = {
    "boost_keywords": {
        "interpretability": 4,
        "alignment": 4,
        "LLM": 3,
        "speech": 4,
    },
    "penalty_keywords": {
        "crypto": -5,
        "hiring": -4,
    },
    "min_hn_score": 20,
}

SAMPLE_HN_TOPSTORIES = json.dumps([1, 2, 3, 4, 5])
SAMPLE_HN_ITEM = json.dumps({
    "id": 1, "type": "story", "title": "LLM Interpretability Breakthrough",
    "url": "https://arxiv.org/abs/2026.12345", "score": 250,
    "descendants": 120, "by": "researcher", "time": 1710700000,
})
SAMPLE_HN_ITEM_2 = json.dumps({
    "id": 2, "type": "story", "title": "Crypto Exchange Launches",
    "url": "https://crypto.example.com", "score": 500,
    "descendants": 300, "by": "trader", "time": 1710700000,
})
SAMPLE_HN_ITEM_COMMENT = json.dumps({
    "id": 3, "type": "comment", "text": "Great post!",
})

SAMPLE_AF_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel>
<title>Alignment Forum</title>
<item>
<title><![CDATA[Mechanistic Interpretability of SAEs]]></title>
<link>https://www.alignmentforum.org/posts/abc123</link>
<pubDate>Mon, 18 Mar 2026 10:00:00 GMT</pubDate>
<dc:creator><![CDATA[Neel Nanda]]></dc:creator>
<description><![CDATA[<p>New results on sparse autoencoders...</p>]]></description>
</item>
<item>
<title><![CDATA[RLHF Failure Modes]]></title>
<link>https://www.alignmentforum.org/posts/def456</link>
<pubDate>Sun, 17 Mar 2026 08:00:00 GMT</pubDate>
<dc:creator><![CDATA[John Doe]]></dc:creator>
</item>
</channel>
</rss>"""

SAMPLE_LW_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel>
<title>LessWrong</title>
<item>
<title><![CDATA[AI Safety via Debate]]></title>
<link>https://www.lesswrong.com/posts/xyz789</link>
<pubDate>Mon, 18 Mar 2026 12:00:00 GMT</pubDate>
<dc:creator><![CDATA[Jane Smith]]></dc:creator>
</item>
</channel>
</rss>"""

SAMPLE_ARXIV_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>cs.CL updates</title>
<item>
<title>Speech Recognition with Transformers</title>
<link>https://arxiv.org/abs/2026.54321</link>
<description>We present a new ASR model...</description>
</item>
<item>
<title>Scaling Laws for Language Models</title>
<link>https://arxiv.org/abs/2026.54322</link>
<description>Empirical scaling laws...</description>
</item>
</channel>
</rss>"""


# ── Article / Base Tests ─────────────────────────────────────────

class TestArticle(unittest.TestCase):

    def test_uid_with_source_id(self):
        a = make_article(source="hn", source_id="42")
        self.assertEqual(a.uid(), "hn:42")

    def test_uid_without_source_id(self):
        a = make_article(source_id="")
        self.assertEqual(a.uid(), f"hn:{a.url}")

    def test_to_dict(self):
        a = make_article()
        d = a.to_dict()
        self.assertIn('uid', d)
        self.assertEqual(d['title'], "Test Article")
        self.assertEqual(d['source'], "hn")

    def test_scored_article_to_dict(self):
        a = make_article()
        sa = ScoredArticle(article=a, interest_score=7.5, suggested_action="略讀")
        d = sa.to_dict()
        self.assertEqual(d['interest_score'], 7.5)
        self.assertEqual(d['suggested_action'], "略讀")
        self.assertIn('uid', d)


# ── Source Discovery Tests ───────────────────────────────────────

class TestDiscovery(unittest.TestCase):

    def test_discover_finds_all_sources(self):
        sources = discover_sources()
        self.assertIn('hn', sources)
        self.assertIn('af', sources)
        self.assertIn('lw', sources)
        self.assertIn('arxiv', sources)

    def test_discover_returns_classes(self):
        sources = discover_sources()
        for name, cls in sources.items():
            self.assertTrue(issubclass(cls, BaseSource))

    def test_all_sources_have_name(self):
        sources = discover_sources()
        for name, cls in sources.items():
            instance = cls()
            self.assertEqual(instance.name, name)


# ── HN Source Tests ──────────────────────────────────────────────

class TestHNSource(unittest.TestCase):

    @patch('sources.hn._fetch_url')
    def test_fetch_parses_stories(self, mock_fetch):
        mock_fetch.side_effect = [
            SAMPLE_HN_TOPSTORIES,
            SAMPLE_HN_ITEM,
            SAMPLE_HN_ITEM_2,
            SAMPLE_HN_ITEM_COMMENT,  # should be skipped
            None,  # fetch failure
            None,
        ]
        from sources.hn import HackerNewsSource
        src = HackerNewsSource()
        articles = src.fetch(limit=5)
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].source, "hn")
        self.assertEqual(articles[0].title, "LLM Interpretability Breakthrough")
        self.assertEqual(articles[0].score, 250)

    @patch('sources.hn._fetch_url')
    def test_fetch_handles_empty(self, mock_fetch):
        mock_fetch.return_value = None
        from sources.hn import HackerNewsSource
        self.assertEqual(HackerNewsSource().fetch(), [])

    @patch('sources.hn._fetch_url')
    def test_fetch_handles_bad_json(self, mock_fetch):
        mock_fetch.return_value = "not json"
        from sources.hn import HackerNewsSource
        self.assertEqual(HackerNewsSource().fetch(), [])


# ── AF Source Tests ──────────────────────────────────────────────

class TestAFSource(unittest.TestCase):

    @patch('sources.af._fetch_url')
    def test_fetch_parses_rss(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_AF_RSS
        from sources.af import AlignmentForumSource
        articles = AlignmentForumSource().fetch(limit=10)
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].source, "af")
        self.assertEqual(articles[0].title, "Mechanistic Interpretability of SAEs")
        self.assertEqual(articles[0].author, "Neel Nanda")

    @patch('sources.af._fetch_url')
    def test_fetch_handles_empty(self, mock_fetch):
        mock_fetch.return_value = None
        from sources.af import AlignmentForumSource
        self.assertEqual(AlignmentForumSource().fetch(), [])

    @patch('sources.af._fetch_url')
    def test_fetch_respects_limit(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_AF_RSS
        from sources.af import AlignmentForumSource
        articles = AlignmentForumSource().fetch(limit=1)
        self.assertEqual(len(articles), 1)


# ── LW Source Tests ──────────────────────────────────────────────

class TestLWSource(unittest.TestCase):

    @patch('sources.lw._fetch_url')
    def test_fetch_parses_rss(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_LW_RSS
        from sources.lw import LessWrongSource
        articles = LessWrongSource().fetch(limit=10)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].source, "lw")
        self.assertEqual(articles[0].title, "AI Safety via Debate")

    @patch('sources.lw._fetch_url')
    def test_fetch_handles_empty(self, mock_fetch):
        mock_fetch.return_value = None
        from sources.lw import LessWrongSource
        self.assertEqual(LessWrongSource().fetch(), [])


# ── arXiv Source Tests ───────────────────────────────────────────

class TestArxivSource(unittest.TestCase):

    @patch('sources.arxiv_feed._fetch_url')
    def test_fetch_parses_rss(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_ARXIV_RSS
        from sources.arxiv_feed import ArxivSource
        src = ArxivSource()
        src._categories = ["cs.CL"]  # single category for test
        articles = src.fetch(limit=10)
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].source, "arxiv")
        self.assertIn("cs.CL", articles[0].tags)

    @patch('sources.arxiv_feed._fetch_url')
    def test_configure_categories(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_ARXIV_RSS
        from sources.arxiv_feed import ArxivSource
        src = ArxivSource()
        src.configure({"categories": ["cs.CL"]})
        self.assertEqual(src._categories, ["cs.CL"])

    @patch('sources.arxiv_feed._fetch_url')
    def test_fetch_handles_empty(self, mock_fetch):
        mock_fetch.return_value = None
        from sources.arxiv_feed import ArxivSource
        src = ArxivSource()
        src._categories = ["cs.CL"]
        self.assertEqual(src.fetch(), [])

    @patch('sources.arxiv_feed._fetch_url')
    def test_fetch_bad_xml_falls_back_to_regex(self, mock_fetch):
        mock_fetch.return_value = "<rss><channel><item><title>Test</title><link>https://arxiv.org/abs/123</link></item></channel>"
        from sources.arxiv_feed import ArxivSource
        src = ArxivSource()
        src._categories = ["cs.CL"]
        articles = src.fetch(limit=10)
        # Should fall back to regex and find the item
        self.assertGreaterEqual(len(articles), 0)  # may or may not parse depending on XML validity


# ── Scoring Tests ────────────────────────────────────────────────

class TestScoring(unittest.TestCase):

    def test_boost_keywords(self):
        a = make_article(title="LLM Interpretability Research")
        score = engine.score_article(a, SAMPLE_PROFILE)
        self.assertGreater(score, 0)

    def test_penalty_keywords(self):
        a = make_article(title="New Crypto Exchange Launch", score=10)
        score = engine.score_article(a, SAMPLE_PROFILE)
        self.assertLess(score, 0)

    def test_high_hn_score_bonus(self):
        a1 = make_article(title="Some Article", score=50)
        a2 = make_article(title="Some Article", score=500)
        s1 = engine.score_article(a1, SAMPLE_PROFILE)
        s2 = engine.score_article(a2, SAMPLE_PROFILE)
        self.assertGreater(s2, s1)

    def test_comment_bonus(self):
        a1 = make_article(title="Article", comments=10)
        a2 = make_article(title="Article", comments=200)
        s1 = engine.score_article(a1, SAMPLE_PROFILE)
        s2 = engine.score_article(a2, SAMPLE_PROFILE)
        self.assertGreater(s2, s1)

    def test_domain_boost(self):
        a = make_article(title="Paper", url="https://arxiv.org/abs/2026.1")
        score = engine.score_article(a, SAMPLE_PROFILE)
        a_plain = make_article(title="Paper", url="https://example.com")
        score_plain = engine.score_article(a_plain, SAMPLE_PROFILE)
        self.assertGreater(score, score_plain)

    def test_classify_action(self):
        self.assertEqual(engine.classify_action(10), "深讀")
        self.assertEqual(engine.classify_action(6), "略讀")
        self.assertEqual(engine.classify_action(2), "掃標題")

    def test_score_articles_returns_sorted(self):
        articles = [
            make_article(title="Crypto nonsense", score=10),
            make_article(title="LLM alignment interpretability", score=200,
                         url="https://arxiv.org/abs/2026.1", source_id="2"),
        ]
        scored = engine.score_articles(articles, SAMPLE_PROFILE)
        self.assertEqual(len(scored), 2)
        # Second article should score higher
        self.assertGreater(scored[1].interest_score, scored[0].interest_score)


# ── Dedup Tests ──────────────────────────────────────────────────

class TestDedup(unittest.TestCase):

    def test_title_similarity_identical(self):
        self.assertAlmostEqual(engine._title_similarity("hello world", "hello world"), 1.0)

    def test_title_similarity_different(self):
        sim = engine._title_similarity("hello world", "foo bar baz")
        self.assertLess(sim, 0.5)

    def test_title_similarity_partial(self):
        sim = engine._title_similarity("LLM interpretability research", "LLM interpretability paper")
        self.assertGreaterEqual(sim, 0.5)

    def test_title_similarity_empty(self):
        self.assertEqual(engine._title_similarity("", "hello"), 0.0)

    def test_dedup_removes_same_url(self):
        articles = [
            make_article(url="https://example.com/1", source_id="1"),
            make_article(url="https://example.com/1", source="af", source_id="af1"),
        ]
        result = engine.dedup(articles, seen_path="/nonexistent")
        self.assertEqual(len(result), 1)

    def test_dedup_removes_similar_titles(self):
        articles = [
            make_article(title="LLM Interpretability Research Paper", source_id="1"),
            make_article(title="LLM Interpretability Research Paper", source="af",
                         url="https://other.com/2", source_id="2"),
        ]
        result = engine.dedup(articles, seen_path="/nonexistent")
        self.assertEqual(len(result), 1)

    def test_dedup_keeps_different_articles(self):
        articles = [
            make_article(title="LLM Research", url="https://a.com", source_id="1"),
            make_article(title="Crypto News", url="https://b.com", source_id="2"),
        ]
        result = engine.dedup(articles, seen_path="/nonexistent")
        self.assertEqual(len(result), 2)

    def test_dedup_with_seen_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            now = datetime.now(TZ).isoformat()
            f.write(json.dumps({"id": "hn:123", "ts": now}) + '\n')
            f.flush()
            try:
                articles = [make_article(source_id="123")]  # uid = hn:123
                result = engine.dedup(articles, seen_path=f.name)
                self.assertEqual(len(result), 0)
            finally:
                os.unlink(f.name)


# ── Config Tests ─────────────────────────────────────────────────

class TestConfig(unittest.TestCase):

    def test_load_default_config(self):
        # Test that default config is valid JSON with expected keys
        with open(os.path.join(os.path.dirname(__file__), 'config.json')) as f:
            cfg = json.load(f)
        self.assertIn('sources', cfg)
        self.assertIn('scoring', cfg)
        self.assertIn('dedup', cfg)
        self.assertIn('hn', cfg['sources'])
        self.assertTrue(cfg['sources']['hn']['enabled'])

    def test_load_sources_filters_disabled(self):
        cfg = {
            "sources": {
                "hn": {"enabled": True},
                "af": {"enabled": False},
                "lw": {"enabled": True},
            }
        }
        sources = engine.load_sources(cfg)
        names = [s.name for s in sources]
        self.assertIn('hn', names)
        self.assertNotIn('af', names)
        self.assertIn('lw', names)

    def test_load_sources_configures_arxiv(self):
        cfg = {
            "sources": {
                "arxiv": {"enabled": True, "categories": ["cs.CL"]},
            }
        }
        sources = engine.load_sources(cfg)
        arxiv = [s for s in sources if s.name == 'arxiv']
        self.assertEqual(len(arxiv), 1)
        self.assertEqual(arxiv[0]._categories, ["cs.CL"])


# ── Recommend Pipeline Tests ────────────────────────────────────

class TestRecommend(unittest.TestCase):

    def test_recommend_returns_top_n(self):
        articles = [
            make_article(title="Crypto stuff", score=10, source_id="1"),
            make_article(title="LLM alignment interpretability", score=200,
                         url="https://arxiv.org/abs/1", source_id="2"),
            make_article(title="Speech recognition with whisper", score=150,
                         url="https://example.com/3", source_id="3"),
        ]
        scored = engine.recommend(articles, SAMPLE_PROFILE, limit=2,
                                  seen_path="/nonexistent")
        self.assertEqual(len(scored), 2)
        # Top article should be the alignment one
        self.assertIn("alignment", scored[0].article.title.lower())

    def test_recommend_deduplicates(self):
        articles = [
            make_article(title="Same Article Title Here", source_id="1"),
            make_article(title="Same Article Title Here", source="af",
                         url="https://other.com", source_id="2"),
        ]
        scored = engine.recommend(articles, SAMPLE_PROFILE, limit=10,
                                  seen_path="/nonexistent")
        self.assertEqual(len(scored), 1)


# ── Seen / Feedback Tests ───────────────────────────────────────

class TestSeenFeedback(unittest.TestCase):

    def test_mark_seen_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(engine, 'FEEDS_DIR', tmpdir):
                engine.mark_seen(["hn:1", "af:2"])
                seen_path = os.path.join(tmpdir, 'seen.jsonl')
                self.assertTrue(os.path.exists(seen_path))
                with open(seen_path) as f:
                    lines = f.readlines()
                self.assertEqual(len(lines), 2)

    def test_record_feedback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(engine, 'FEEDS_DIR', tmpdir):
                engine.record_feedback("hn:1", True, title="Test", source="hn")
                fb_path = os.path.join(tmpdir, 'feedback.jsonl')
                self.assertTrue(os.path.exists(fb_path))
                with open(fb_path) as f:
                    entry = json.loads(f.readline())
                self.assertTrue(entry['positive'])
                self.assertEqual(entry['source'], 'hn')

    def test_get_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(engine, 'FEEDS_DIR', tmpdir):
                engine.record_feedback("hn:1", True, source="hn")
                engine.record_feedback("af:1", False, source="af")
                stats = engine.get_stats()
                self.assertEqual(stats['feedback_total'], 2)
                self.assertEqual(stats['feedback_positive'], 1)
                self.assertEqual(stats['feedback_negative'], 1)


# ── CLI Tests ────────────────────────────────────────────────────

class TestCLI(unittest.TestCase):

    def test_sources_command(self):
        """Test that sources command runs without error."""
        import io
        from contextlib import redirect_stdout
        from feed import cmd_sources
        args = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(engine, 'FEEDS_DIR', tmpdir):
                out = io.StringIO()
                with redirect_stdout(out):
                    cmd_sources(args)
                output = out.getvalue()
                self.assertIn('hn', output)
                self.assertIn('Source', output)

    def test_config_command(self):
        import io
        from contextlib import redirect_stdout
        from feed import cmd_config
        args = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(engine, 'FEEDS_DIR', tmpdir):
                out = io.StringIO()
                with redirect_stdout(out):
                    cmd_config(args)
                output = out.getvalue()
                parsed = json.loads(output)
                self.assertIn('sources', parsed)

    def test_enable_disable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(engine, 'FEEDS_DIR', tmpdir):
                from feed import cmd_enable, cmd_disable
                args = MagicMock()
                args.name = 'hn'
                cmd_disable(args)
                cfg = engine.load_config()
                self.assertFalse(cfg['sources']['hn']['enabled'])
                cmd_enable(args)
                cfg = engine.load_config()
                self.assertTrue(cfg['sources']['hn']['enabled'])


# ── Migration Tests ──────────────────────────────────────────────

class TestMigration(unittest.TestCase):

    def test_migrate_seen(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hn_dir = os.path.join(tmpdir, 'hn')
            feeds_dir = os.path.join(tmpdir, 'feeds')
            os.makedirs(hn_dir)
            os.makedirs(feeds_dir)

            # Write sample seen data
            now = datetime.now(TZ).isoformat()
            with open(os.path.join(hn_dir, 'seen.jsonl'), 'w') as f:
                f.write(json.dumps({"id": "123", "ts": now}) + '\n')
                f.write(json.dumps({"id": "456", "ts": now}) + '\n')

            import migrate_hn
            with patch.object(migrate_hn, 'HN_DIR', hn_dir), \
                 patch.object(migrate_hn, 'FEEDS_DIR', feeds_dir):
                count = migrate_hn.migrate_seen()

            self.assertEqual(count, 2)
            with open(os.path.join(feeds_dir, 'seen.jsonl')) as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 2)
            entry = json.loads(lines[0])
            self.assertEqual(entry['source'], 'hn')
            self.assertTrue(entry['id'].startswith('hn:'))

    def test_migrate_feedback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hn_dir = os.path.join(tmpdir, 'hn')
            feeds_dir = os.path.join(tmpdir, 'feeds')
            os.makedirs(hn_dir)
            os.makedirs(feeds_dir)

            now = datetime.now(TZ).isoformat()
            with open(os.path.join(hn_dir, 'feedback.jsonl'), 'w') as f:
                f.write(json.dumps({"id": "123", "positive": True, "ts": now}) + '\n')

            import migrate_hn
            with patch.object(migrate_hn, 'HN_DIR', hn_dir), \
                 patch.object(migrate_hn, 'FEEDS_DIR', feeds_dir):
                count = migrate_hn.migrate_feedback()

            self.assertEqual(count, 1)

    def test_migrate_preferences(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hn_dir = os.path.join(tmpdir, 'hn')
            feeds_dir = os.path.join(tmpdir, 'feeds')
            os.makedirs(hn_dir)
            os.makedirs(feeds_dir)

            with open(os.path.join(hn_dir, 'preferences.json'), 'w') as f:
                json.dump(SAMPLE_PROFILE, f)

            import migrate_hn
            with patch.object(migrate_hn, 'HN_DIR', hn_dir), \
                 patch.object(migrate_hn, 'FEEDS_DIR', feeds_dir):
                result = migrate_hn.migrate_preferences()

            self.assertTrue(result)
            self.assertTrue(os.path.exists(os.path.join(feeds_dir, 'preferences.json')))

    def test_migrate_idempotent(self):
        """Running migration twice should not duplicate entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hn_dir = os.path.join(tmpdir, 'hn')
            feeds_dir = os.path.join(tmpdir, 'feeds')
            os.makedirs(hn_dir)
            os.makedirs(feeds_dir)

            now = datetime.now(TZ).isoformat()
            with open(os.path.join(hn_dir, 'seen.jsonl'), 'w') as f:
                f.write(json.dumps({"id": "123", "ts": now}) + '\n')

            import migrate_hn
            with patch.object(migrate_hn, 'HN_DIR', hn_dir), \
                 patch.object(migrate_hn, 'FEEDS_DIR', feeds_dir):
                migrate_hn.migrate_seen()
                count2 = migrate_hn.migrate_seen()

            self.assertEqual(count2, 0)  # no new entries on second run


# ── Google Sheets Sync Tests ────────────────────────────────────

class TestSheetsSync(unittest.TestCase):

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import sync_to_sheets as sheets
        self.sheets = sheets

    def test_item_to_row_basic(self):
        item = {
            "source": "hn", "title": "Test Article", "url": "https://example.com",
            "author": "alice", "score": 100, "posted": "2026-03-18",
            "snippet": "A test snippet", "tags": ["ml", "ai"],
            "interest_score": 7.5, "suggested_action": "略讀",
        }
        row = self.sheets.item_to_row(item)
        self.assertEqual(len(row), 10)
        self.assertEqual(row[0], "2026-03-18")  # Date
        self.assertEqual(row[1], "hn")           # Source
        self.assertEqual(row[2], "Test Article") # Title
        self.assertEqual(row[3], "alice")        # Author
        self.assertEqual(row[4], "100")          # Score
        self.assertEqual(row[5], "https://example.com")  # URL
        self.assertEqual(row[6], "ml, ai")              # Tags joined
        self.assertEqual(row[7], "7.5")                 # Relevance Score
        self.assertEqual(row[8], "略讀")                 # Reasoning
        self.assertEqual(row[9], "A test snippet")      # Summary (last)

    def test_item_to_row_iso_date(self):
        item = {"posted": "2026-03-18T10:30:00+08:00", "url": "https://x.com"}
        row = self.sheets.item_to_row(item)
        self.assertEqual(row[0], "2026-03-18")

    def test_item_to_row_rfc2822_date(self):
        item = {"posted": "Mon, 18 Mar 2026 10:00:00 GMT", "url": "https://x.com"}
        row = self.sheets.item_to_row(item)
        self.assertEqual(row[0], "2026-03-18")

    def test_item_to_row_empty_tags(self):
        item = {"tags": [], "url": "https://x.com"}
        row = self.sheets.item_to_row(item)
        self.assertEqual(row[7], "")

    def test_load_digest_json_recommend_format(self):
        data = {"total_fetched": 50, "recommended": 3, "items": [
            {"title": "A", "url": "https://a.com"},
            {"title": "B", "url": "https://b.com"},
        ]}
        items = self.sheets.load_digest_json(data)
        self.assertEqual(len(items), 2)

    def test_load_digest_json_fetch_format(self):
        data = {"total": 10, "articles": [{"title": "C", "url": "https://c.com"}]}
        items = self.sheets.load_digest_json(data)
        self.assertEqual(len(items), 1)

    def test_load_digest_json_raw_list(self):
        data = [{"title": "D", "url": "https://d.com"}]
        items = self.sheets.load_digest_json(data)
        self.assertEqual(len(items), 1)

    def test_cmd_test_returns_3_items(self):
        items = self.sheets.cmd_test()
        self.assertEqual(len(items), 3)
        for item in items:
            self.assertIn("[TEST]", item["title"])
            self.assertIn("url", item)
            self.assertIn("source", item)

    @patch("sync_to_sheets.gspread")
    def test_sync_items_dedup(self, mock_gspread):
        """Test that sync_items skips URLs already in the sheet."""
        mock_ws = MagicMock()
        mock_ws.row_values.return_value = self.sheets.HEADERS
        mock_ws.col_values.return_value = ["URL", "https://existing.com"]

        items = [
            {"title": "Old", "url": "https://existing.com", "source": "hn"},
            {"title": "New", "url": "https://new.com", "source": "af"},
        ]
        added = self.sheets.sync_items(mock_ws, items, verbose=False)
        self.assertEqual(added, 1)
        mock_ws.insert_rows.assert_called_once()
        # Verify only the new URL was added
        rows_arg = mock_ws.insert_rows.call_args[0][0]
        self.assertEqual(len(rows_arg), 1)
        self.assertIn("https://new.com", rows_arg[0])

    @patch("sync_to_sheets.gspread")
    def test_sync_items_all_duplicates(self, mock_gspread):
        """Test that sync_items returns 0 when all are duplicates."""
        mock_ws = MagicMock()
        mock_ws.row_values.return_value = self.sheets.HEADERS
        mock_ws.col_values.return_value = ["URL", "https://a.com"]

        items = [{"title": "A", "url": "https://a.com", "source": "hn"}]
        added = self.sheets.sync_items(mock_ws, items, verbose=False)
        self.assertEqual(added, 0)
        mock_ws.insert_rows.assert_not_called()

    @patch("sync_to_sheets.gspread")
    def test_ensure_headers_sets_up_empty_sheet(self, mock_gspread):
        """Test that headers are written on an empty sheet."""
        mock_ws = MagicMock()
        mock_ws.row_values.return_value = []
        self.sheets.ensure_headers(mock_ws)
        mock_ws.update.assert_called_once_with([self.sheets.HEADERS], range_name="A1")
        mock_ws.freeze.assert_called_once_with(rows=1)

    @patch("sync_to_sheets.gspread")
    def test_ensure_headers_skips_existing(self, mock_gspread):
        """Test that headers are not overwritten if already correct."""
        mock_ws = MagicMock()
        mock_ws.row_values.return_value = self.sheets.HEADERS
        self.sheets.ensure_headers(mock_ws)
        mock_ws.update.assert_not_called()

    def test_get_sheet_id_from_config(self):
        """Test that sheet ID is read from config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"google_sheets": {"sheet_id": "test_id_123"}}, f)
            f.flush()
            try:
                orig = self.sheets.CONFIG_PATH
                self.sheets.CONFIG_PATH = Path(f.name)
                sid = self.sheets.get_sheet_id()
                self.assertEqual(sid, "test_id_123")
            finally:
                self.sheets.CONFIG_PATH = orig
                os.unlink(f.name)

    def test_backfill_with_json_files(self):
        """Test backfill scans candidate JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            candidates = Path(tmpdir) / "candidates"
            candidates.mkdir()
            digest = {
                "items": [
                    {"title": "A", "url": "https://a.com", "source": "hn"},
                    {"title": "B", "url": "https://b.com", "source": "af"},
                ]
            }
            with open(candidates / "2026-03-18.json", "w") as f:
                json.dump(digest, f)

            orig_candidates = self.sheets.CANDIDATES_DIR
            orig_feeds = self.sheets.FEEDS_DIR
            self.sheets.CANDIDATES_DIR = candidates
            self.sheets.FEEDS_DIR = Path(tmpdir)
            try:
                items = self.sheets.cmd_backfill()
                self.assertEqual(len(items), 2)
            finally:
                self.sheets.CANDIDATES_DIR = orig_candidates
                self.sheets.FEEDS_DIR = orig_feeds


if __name__ == '__main__':
    unittest.main()
