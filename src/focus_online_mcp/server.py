"""MCP server: unofficial read-only access to FOCUS online
(focus.de) — one of Germany's biggest news magazines — via its
official RSS feed (one feed, ~400 items) and article pages
(server-rendered <article> text; the JSON-LD articleBody is absent
on FOCUS pages).
No key, no login."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import domain as _dom
from . import http as _http

INSTRUCTIONS = """\
Unofficial read-only MCP server for FOCUS online (focus.de) — one
of Germany's biggest news magazines — via its official RSS feed
(no key, no login) and article pages. The main feed (~400 items,
newest first) with kicker, teaser, section, author and image; news
by section (politik, kultur, panorama, sport, finanzen, earth,
... — sections are derived from the article links, because
per-section feeds do not exist on focus.de); a section overview
with item counts; keyword search across the whole feed; and full
article text (server-rendered <article> paragraphs — the JSON-LD
articleBody is absent on FOCUS pages). NOTE: there is only ONE
feed — /rss/<section>/ 404s and /rss/<section>.xml redirects to
the main feed — so section filtering runs client-side over the
400-item feed. FOCUS+ paid content exists (launched May 2025);
sampled pages (including one from the "Das Beste von FOCUS+"
shelf) returned full text, and a page that ever gates returns
paywalled=true with the teaser only, never fabricated text.
Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · \
https://mabbasi.ir — Germany MCP factory.\
"""


_SOURCE = "www.focus.de"
_DISCLAIMER = "Unofficial read-only data from FOCUS online's public RSS feed and article pages; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


mcp = FastMCP("focus-online-mcp", instructions=INSTRUCTIONS)


def _feed(limit: int) -> dict:
    """Fetch the FOCUS online RSS feed and return its items, newest first."""
    parsed = _dom.parse_rss(_http.fetch_feed(_dom.FEED_URL))
    items = parsed["items"][:limit]
    return {
        "feed_title": parsed["feed_title"],
        "total_results": parsed["count"],
        "count": len(items),
        "items": items,
    }


@mcp.tool()
def focus_headlines(limit: int = 10) -> str:
    """Top FOCUS online headlines (official RSS feed, ~400 items),
newest first. limit: 1..150 (default 10). Items carry title,
kicker, link (a per-article URL for focus_get_article), teaser,
section (from the link path), author, publish time and image."""
    try:
        lim = _dom.validate_limit(limit)
        out = _feed(lim)
    except (_http.FocusError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def focus_news_by_section(section: str, limit: int = 10) -> str:
    """Newest FOCUS online news of one section, filtered from the
official RSS feed (~400 items). section: e.g. "politik",
"kultur", "panorama", "sport", "finanzen", "earth",
"gesundheit", "auto", "wissen" — focus_sections lists the
sections in today's feed with their counts. limit: 1..150
(default 10). Items carry title, kicker, link (a per-article URL
for focus_get_article), teaser, author, publish time and image."""
    try:
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.FEED_URL))
        available = [s["section"] for s in _dom.sections_of(parsed["items"])]
        sec = _dom.validate_section(section, available)
        items = [it for it in parsed["items"] if it.get("section") == sec]
        out = {
            "section": sec,
            "feed_title": parsed["feed_title"],
            "total_results": len(items),
            "count": min(lim, len(items)),
            "items": items[:lim],
        }
    except (_http.FocusError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def focus_sections() -> str:
    """Sections in today's FOCUS online feed with their item counts,
most items first (derived from the article links — per-section
feeds do not exist on focus.de). Use these section names with
focus_news_by_section."""
    try:
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.FEED_URL))
        secs = _dom.sections_of(parsed["items"])
        out = {
            "feed_title": parsed["feed_title"],
            "total_results": parsed["count"],
            "sections": secs,
        }
    except (_http.FocusError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def focus_search_news(query: str, limit: int = 10) -> str:
    """Search FOCUS online news by keyword (title + kicker + teaser)
across the whole official RSS feed (~400 items). query: free text,
e.g. "Trump" or "Bundesliga". limit: 1..150 (default 10). Searches
client-side, newest first, de-duplicated by link."""
    try:
        if not (query or "").strip():
            return _ok({"error": "query must not be empty"})
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.FEED_URL))
        found = _dom.dedupe_sort(_dom.search_items(parsed["items"], query.strip()))
        out = {
            "query": query.strip(),
            "total_results": len(found),
            "count": min(lim, len(found)),
            "items": found[:lim],
        }
    except (_http.FocusError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def focus_get_article(url: str) -> str:
    """Full text of one FOCUS online article page (server-rendered
<article> paragraphs — the JSON-LD articleBody is absent on FOCUS
pages). url: a www.focus.de article URL, e.g. from
focus_headlines (/<section>/<slug>_<uuid>.html) or a /rechner/
service page. Returns title, author, publish time, the body text
and its word count. Live-ticker pages ("... im Live-Ticker ...")
carry no entry text in SSR — they return kind="live-ticker" with
only the latest entry's headline. A page that is not freely
accessible returns paywalled=true with the teaser only. Nothing
is ever fabricated."""
    try:
        if not (url or "").strip():
            return _ok({"error": "url must not be empty"})
        url = url.strip()
        article = _dom.parse_article(_http.fetch_article(url))
        paywalled = article["paywalled"]
        note = ""
        if paywalled:
            note = (
                "This article is not freely accessible: only the teaser "
                "is available."
            )
        elif article["kind"] == "video":
            note = (
                "Video page: the description is the whole freely "
                "available text; watch the video at video_url."
            )
        elif article["kind"] == "live-ticker":
            note = (
                "Live-ticker page: the entries load client-side, so "
                "only the latest entry's headline is available in the "
                "server-rendered page."
            )
        elif article["teaser_only"]:
            note = (
                "Only the teaser is available for this item; the teaser "
                "is the whole freely available text."
            )
        out = {
            "url": url,
            "title": article["title"],
            "author": article["author"],
            "published": article["published"],
            "kind": article["kind"],
            "paywalled": paywalled,
            "teaser_only": article["teaser_only"],
            "word_count": article["word_count"],
            "body": article["body"],
            "description": article["description"],
            "video_url": article["video_url"],
            "duration": article["duration"],
            "note": note,
        }
    except (_http.FocusError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def focus_health() -> str:
    """Check whether the FOCUS online RSS feed is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
