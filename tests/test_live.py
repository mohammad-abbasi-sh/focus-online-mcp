"""Live tests — hit the real www.focus.de RSS feed and article
pages. Cautious: few requests.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set FOCUS_SKIP_LIVE=1)
"""
import json
import os
import pathlib
import sys
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from focus_online_mcp import server as srv

pytestmark = pytest.mark.live
SKIP = os.environ.get("FOCUS_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="FOCUS_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_headlines_live(self):
        out = json.loads(srv.focus_headlines(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["title"] and i["description"] for i in out["items"]))
        print(f"\nLIVE headlines: {out['count']} items, first: {out['items'][0]['title']}")

    def test_by_section_live(self):
        out = json.loads(srv.focus_news_by_section("politik", limit=3))
        self.assertNotIn("error", out)
        self.assertEqual(out["section"], "politik")
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["section"] == "politik" for i in out["items"]))
        print(f"\nLIVE politik: {out['total_results']} items")

    def test_sections_live(self):
        out = json.loads(srv.focus_sections())
        self.assertNotIn("error", out)
        self.assertGreaterEqual(len(out["sections"]), 5)
        names = [s["section"] for s in out["sections"]]
        self.assertIn("politik", names)
        print(f"\nLIVE sections: {out['sections'][:5]}")

    def test_search_live(self):
        out = json.loads(srv.focus_search_news("Trump", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(
            "trump" in (i["title"] + (i["kicker"] or "") + i["description"]).casefold()
            for i in out["items"]
        ))
        print(f"\nLIVE search 'Trump': {out['total_results']} hits")

    def test_get_article_live(self):
        # An article from the current feed: SSR body expected
        # (FOCUS' JSON-LD articleBody is absent). Live-ticker pages
        # carry no entry text in SSR, so the first non-ticker item
        # is used.
        feed = json.loads(srv.focus_headlines(limit=10))
        self.assertNotIn("error", feed)
        self.assertGreater(len(feed["items"]), 0)
        link = next(
            i["link"] for i in feed["items"]
            if "live-ticker" not in i["link"]
        )
        out = json.loads(srv.focus_get_article(link))
        self.assertNotIn("error", out)
        self.assertFalse(out["paywalled"])
        self.assertEqual(out["kind"], "article")
        self.assertGreater(out["word_count"], 100)
        print(f"\nLIVE article: {out['word_count']} words, {out['title'][:60]}")

    def test_health_live(self):
        out = json.loads(srv.focus_health())
        self.assertNotIn("error", out)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["http_status"], 200)
        print(f"\nLIVE health: {out['status']}")
