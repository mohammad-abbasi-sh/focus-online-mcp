"""Offline tests — parse the real captured focus.de RSS feed and
three real article pages (a finanzen NewsArticle, a "Das Beste von
FOCUS+" earth article, and a /rechner/ service page with an embedded
VideoObject — in all three the JSON-LD articleBody is absent, so the
body comes from the server-rendered <article> paragraphs), no network."""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from focus_online_mcp import domain as dom
from focus_online_mcp import http as http_mod

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


class TestHeadlinesFeed:
    def test_feed_shape(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        assert parsed["feed_title"] == "FOCUS online - Aktuelle Nachrichten"
        assert parsed["count"] == 6
        assert len(parsed["items"]) == 6

    def test_first_item(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        first = parsed["items"][0]
        assert first["title"] == (
            "Vom Boom zum Absturz: Die Trump-Wette geht nicht mehr auf"
        )
        assert first["kicker"] == "Milliardenverluste für Anleger"
        assert first["link"] == (
            "https://www.focus.de/finanzen/"
            "vom-boom-zum-absturz-die-trump-wette-geht-nicht-mehr-auf_"
            "3f006815-3ea2-4d90-9562-653aad882a67.html"
        )
        assert first["description"].startswith(
            "Donald Trumps geschätztes Vermögen ist seit September 2025"
        )
        # Section comes from the link path; the feed has no <category>.
        assert first["section"] == "finanzen"
        assert first["author"] == "Ansgar Graw"
        assert first["published"] == "2026-11-21T10:09:00+00:00"
        assert first["image_url"].startswith(
            "https://quadro.burda-forward.de/"
        )

    def test_items_may_lack_author(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        # dc:creator is present on only ~57% of live items.
        assert parsed["items"][2]["author"] is None
        assert parsed["items"][2]["section"] == "kultur"
        assert all(i["title"] and i["description"] for i in parsed["items"])
        assert all(i["link"].startswith("https://www.focus.de/")
                    for i in parsed["items"])

    def test_sections_of(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        secs = dom.sections_of(parsed["items"])
        assert secs[0] == {"section": "politik", "count": 2}
        assert {s["section"] for s in secs} == {
            "politik", "finanzen", "kultur", "wissen", "sport",
        }
        assert sum(s["count"] for s in secs) == 6


class TestArticles:
    def test_trump_article(self):
        art = dom.parse_article(_read("article-trump.html"))
        assert art["kind"] == "article"
        assert art["title"] == (
            "Vom Boom zum Absturz: Die Trump-Wette geht nicht mehr auf"
        )
        assert art["author"] == "Ansgar Graw"
        assert art["published"] == "2026-11-21T10:09:00.000Z"
        assert art["word_count"] == 826
        assert art["paywalled"] is False
        assert art["teaser_only"] is False
        assert art["video_url"] is None

    def test_trump_body_is_ssr_and_clean(self):
        art = dom.parse_article(_read("article-trump.html"))
        assert art["body"].startswith(
            "Ein Abendessen mit dem Präsidenten zum Schnäppchenpreis"
        )
        # The header <h2> (title again) is dropped; real subheads stay.
        assert "Aktienkorb halbierte sich seit Jahresbeginn" in art["body"]
        assert "Was vom Trump-Boom bleibt" in art["body"]
        # The Google-preferred-source prompt + heading are dropped.
        assert "bevorzugte Quelle" not in art["body"]
        # The teaser paragraph must not repeat at the top of the body.
        assert not art["body"].startswith(art["description"][:40])

    def test_plus_article_is_free_and_full(self):
        # From the homepage's "Das Beste von FOCUS+" shelf: the
        # paywalled-suspect article still returns full SSR text.
        art = dom.parse_article(_read("article-plus.html"))
        assert art["kind"] == "article"
        assert art["title"] == (
            "Versehen in der Nordsee: Greenpeace legt Windpark "
            "buchstäblich Steine in den Weg"
        )
        assert art["author"] == "Leonhard Frey"
        assert art["word_count"] == 655
        assert art["paywalled"] is False
        assert art["body"].startswith(
            "Greenpeace legt Windpark buchstäblich Steine in den Weg"
        )
        # Everything from "Bildquelle:" on (ad + price lines) is cut,
        # including the ad block's "Kleines Kraftwerk" heading.
        assert "Bildquelle" not in art["body"]
        assert "Kleines Kraftwerk" not in art["body"]
        assert "1799 Euro" not in art["body"]
        assert art["body"].endswith(
            "mehr Schweinswal-Bewegungen erfasst als in den "
            "angrenzenden Meeresflächen."
        )

    def test_rechner_article_with_video_object(self):
        # The page carries a VideoObject block BEFORE its NewsArticle
        # block, and the NewsArticle articleBody is absent: the body
        # must still come from the <article> paragraphs, not from
        # the video description.
        art = dom.parse_article(_read("article-rechner.html"))
        assert art["kind"] == "article"
        assert art["title"] == (
            "Gehaltsvergleich: So gut verdienen Sie im Vergleich zu "
            "anderen in Deutschland"
        )
        assert art["author"] == "Philine Lietzmann"
        assert art["word_count"] == 383
        assert art["paywalled"] is False
        assert art["body"].startswith(
            "So gut verdienen Sie im Vergleich zu anderen Deutschen"
        )
        # The trailing "FOCUS+" ad heading + "Bildquelle:" block are cut.
        assert "Bildquelle" not in art["body"]
        assert "Immer-Plus-Depot" not in art["body"]
        assert art["video_url"] is None

    def test_ticker_page_is_labelled(self):
        # Live-ticker pages carry no entry text in SSR — only the
        # latest entry's headline. They must be labelled, not
        # mistaken for a short article.
        art = dom.parse_article(_read("article-ticker.html"))
        assert art["kind"] == "live-ticker"
        assert art["word_count"] == 11
        assert art["paywalled"] is False
        assert "Selenskyj droht" in art["body"]


class TestValidators:
    def test_limit(self):
        assert dom.validate_limit(1) == 1
        assert dom.validate_limit(150) == 150
        with pytest.raises(ValueError):
            dom.validate_limit(0)
        with pytest.raises(ValueError):
            dom.validate_limit(151)

    def test_section(self):
        available = ["politik", "finanzen", "kultur"]
        assert dom.validate_section("Politik", available) == "politik"
        assert dom.validate_section(" FINANZEN ", available) == "finanzen"
        with pytest.raises(ValueError):
            dom.validate_section("bundesliga", available)


class TestSearchAndDedupe:
    def test_search_items(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        found = dom.search_items(parsed["items"], "Trump")
        assert len(found) == 1
        assert found[0]["section"] == "finanzen"
        # Kicker is searched too, case-insensitively.
        assert dom.search_items(parsed["items"], "milliardenverluste") == found
        assert dom.search_items(parsed["items"], "TRUMP") == found
        with pytest.raises(ValueError):
            dom.search_items(parsed["items"], "   ")

    def test_dedupe_sort(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        doubled = parsed["items"] + parsed["items"][:3]
        out = dom.dedupe_sort(doubled)
        assert len(out) == 6
        pubs = [i["published"] for i in out]
        assert pubs == sorted(pubs, reverse=True)


class TestFeedGuards:
    def test_parse_rss_rejects_garbage(self):
        with pytest.raises(ValueError):
            dom.parse_rss("<html><body>not rss</body></html>")

    def test_fetch_feed_refuses_non_feed_urls(self):
        with pytest.raises(http_mod.FocusError):
            http_mod.fetch_feed("https://www.focus.de/rss/politik/")
        with pytest.raises(http_mod.FocusError):
            http_mod.fetch_feed("https://www.focus.de/politik/")

    def test_fetch_article_refuses_fragments(self):
        with pytest.raises(http_mod.FocusError):
            http_mod.fetch_article(
                "https://www.focus.de/finanzen/xxx_123.html#n1"
            )

    def test_fetch_article_refuses_non_article_paths(self):
        with pytest.raises(http_mod.FocusError):
            http_mod.fetch_article("https://www.focus.de/rss/")
        with pytest.raises(http_mod.FocusError):
            http_mod.fetch_article("https://www.focus.de/focusplus/")

    def test_fetch_article_refuses_other_hosts(self):
        with pytest.raises(http_mod.FocusError):
            http_mod.fetch_article(
                "https://www.spiegel.de/politik/xxx-a-123.html"
            )


class TestServerEnvelope:
    def test_tools_return_json_envelope(self):
        # Offline: the tools hit the network, so only the error path
        # is exercised here — but the envelope shape is the same.
        from focus_online_mcp import server as srv

        out = json.loads(srv.focus_news_by_section("bundesliga"))
        assert "error" in out
        assert out["source"] == "www.focus.de"
        assert "fetched_at" in out
