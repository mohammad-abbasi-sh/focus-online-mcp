"""Domain logic: shape FOCUS online's official RSS feed and article
pages into compact dicts (stdlib only).

Data source: the official FOCUS online RSS feed
(https://www.focus.de/rss/ — one feed, ~400 items, no key, no login)
plus article pages, whose full text lives in the server-rendered
<article> paragraphs (the JSON-LD NewsArticle block carries no
articleBody on FOCUS pages).

Honest limitations (verified live 2026-11-21):
- There is ONE feed only. Per-section feeds do not exist:
  /rss/<section>/ 404s for every section tried (politik, wirtschaft,
  sport, kultur, digital, panorama, wissen, gesundheit, auto, reisen,
  geld) and /rss/<section>.xml 301-redirects to the main feed.
  Sections are therefore derived from each item's link path
  (politik 80, kultur 80, panorama 64, sport 43, finanzen 39,
  earth 20, ... in the 2026-11-21 feed) and
  focus_news_by_section filters the main feed client-side.
- The feed carries no <category> tags and media:category is always
  "news"; the <kicker> is the item's eyebrow line and dc:creator
  (present on ~57% of items) is the author. content:encoded holds
  only the kicker + "Author: ..." line, not the body.
- Article pages carry a JSON-LD NewsArticle block (headline,
  description, author, datePublished) but NO articleBody and NO
  isAccessibleForFree field on the sampled free pages, so the body
  is always read from the server-rendered <article> paragraphs
  (5,867 chars sampled on a finanzen article). A page that ever
  sets isAccessibleForFree=false, or that shows paywall markers
  with only a stub body, returns paywalled=true with the teaser.
- FOCUS+ paid content exists (launched May 2025; Plus articles are
  mixed into the free content) — but the one sampled article from
  the homepage's "Das Beste von FOCUS+" shelf returned its FULL
  text server-side (17 paragraphs, 4,702 chars), so no paywalled
  sample could be validated; the paywall path above is defensive
  and documented, not observed.
- Trailing boilerplate inside <article> is filtered: everything
  from the first "Bildquelle:" paragraph on (ads / related-article
  teasers), the "bevorzugte Quelle bei Google" prompt paragraph
  and its heading, and bare price lines ("1799 Euro"). The first
  <h2> repeats the headline and is dropped; later <h2> subheads
  are kept as body lines.
- Article pages may embed a VideoObject block as well; a page with
  a NewsArticle block is still treated as an article, never as a
  video page.
- Live-ticker pages ("... im Live-Ticker ...") carry NO entry text
  in SSR — the entries load client-side; only the latest entry's
  headline is in the server-rendered page. They are labelled
  kind="live-ticker" (verified live 2026-11-21 on the
  Ukraine-Krieg ticker: 11 words) so callers are not misled by
  the tiny body.
"""
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

BASE = "https://www.focus.de"
FEED_URL = f"{BASE}/rss/"

# Sections observed in the live 2026-11-21 feed (link-path first
# segment). The set is re-derived from each fetched feed, so a
# section that appears later is accepted automatically; this list
# is only documentation for the tool text.
KNOWN_SECTIONS = (
    "politik", "kultur", "panorama", "sport", "finanzen", "earth",
    "gesundheit", "auto", "die-debatte", "wissen", "immobilien",
    "reisen", "tagesthema", "familie", "wetter", "regional",
    "digital",
)

_DC = "http://purl.org/dc/elements/1.1/"
_MRSS = "http://search.yahoo.com/mrss/"


def validate_limit(limit: int) -> int:
    """Clamp/validate the page size (the feed carries ~400 items)."""
    if not 1 <= limit <= 150:
        raise ValueError(f"limit out of range: {limit} (expected 1..150)")
    return limit


def section_of_link(link: str) -> str | None:
    """First path segment of a www.focus.de article URL, e.g. 'politik'."""
    try:
        path = urlparse(link).path.strip("/")
    except ValueError:
        return None
    if not path:
        return None
    seg = path.split("/", 1)[0]
    return seg or None


def validate_section(section: str, available: list[str]) -> str:
    """Normalise a section name to one present in the fetched feed."""
    s = (section or "").strip().casefold()
    if s not in [a.casefold() for a in available]:
        raise ValueError(
            f"unknown section: {section!r} (available in today's feed: "
            f"{', '.join(available)})"
        )
    return s


def _text(elem, tag: str) -> str:
    child = elem.find(tag)
    if child is None or child.text is None:
        return ""
    return html.unescape(child.text).strip()


def _iso(date_text: str) -> str | None:
    if not date_text:
        return None
    text = date_text.strip()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(raw: str) -> str:
    text = _TAG_RE.sub("", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _published(item: ET.Element) -> str | None:
    for child in item:
        local = child.tag.rsplit("}", 1)[-1]
        if local in ("pubDate", "date") and child.text:
            return _iso(child.text)
    return None


def compact_item(item: ET.Element) -> dict:
    """One RSS 2.0 <item>: kicker, title, link, teaser, section
    (from the link path), author, publish time and image."""
    link = _text(item, "link")
    image = None
    media = item.find(f"{{{_MRSS}}}content")
    if media is not None:
        image = media.get("url") or None
    author = _text(item, f"{{{_DC}}}creator") or None
    return {
        "title": _text(item, "title"),
        "kicker": _text(item, "kicker") or None,
        "link": link,
        "description": _strip_tags(_text(item, "description")),
        "section": section_of_link(link),
        "author": author,
        "published": _published(item),
        "image_url": image,
    }


def parse_rss(xml_text: str) -> dict:
    """Parse the FOCUS online RSS 2.0 feed into
    {feed_title, count, items}.

    Raises ValueError on malformed XML or a non-RSS document (e.g. a
    404 error page saved as text).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"invalid RSS XML: {e}") from e
    channel = root.find("channel")
    if channel is None:
        raise ValueError("unexpected RSS shape: no <channel> element")
    items = [compact_item(it) for it in channel.findall("item")]
    return {
        "feed_title": _text(channel, "title"),
        "count": len(items),
        "items": items,
    }


def sections_of(items: list) -> list[dict]:
    """Section counts for a parsed feed, most items first."""
    counts = Counter(
        it.get("section") for it in items if it.get("section")
    )
    return [
        {"section": sec, "count": n}
        for sec, n in counts.most_common()
    ]


_LD_JSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
    re.S | re.I,
)
_ARTICLE_RE = re.compile(r"<article[^>]*>(.*?)</article>", re.S | re.I)
_BLOCK_RE = re.compile(r"<(p|h2)[^>]*>(.*?)</\1>", re.S | re.I)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_OG_DESC_RE = re.compile(
    r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"',
    re.S | re.I,
)
_PRICE_LINE_RE = re.compile(r"^\d+[\.,]?\d*\s*(Euro|€)\s*$")


def _author_name(raw) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        return str(raw.get("name") or "").strip()
    if isinstance(raw, list):
        names = [_author_name(a) for a in raw]
        return ", ".join(n for n in names if n)
    return ""


def _is_free(block: dict) -> bool:
    """isAccessibleForFree from a JSON-LD block; absent means free
    (FOCUS pages that carry the field at all set it explicitly)."""
    val = block.get("isAccessibleForFree")
    return True if val is None else bool(val)


_PAYWALL_MARKERS = (
    "nur für Abonnenten",
    "FOCUS+ Abo",
    "exklusiv für FOCUS+",
    "Paywall",
    "ic-focusplus",
    "Jetzt FOCUS+ abonnieren",
)


def _has_paywall_markers(html_text: str) -> bool:
    return any(m in html_text for m in _PAYWALL_MARKERS)


def _ssr_body(html_text: str, title: str, description: str) -> str:
    """Body text from the server-rendered <article> paragraphs and
    subheads, in document order.

    Filters out the header <h2> (the title again), the teaser
    paragraph (a repeat of the description), the "bevorzugte Quelle
    bei Google" prompt paragraph + heading, and everything from
    the first "Bildquelle:" paragraph on (ads / related-article
    teasers). Raises ValueError when no usable body paragraphs are
    found.
    """
    match = _ARTICLE_RE.search(html_text)
    if not match:
        raise ValueError(
            "no article text found on this page (no JSON-LD articleBody "
            "and no <article> body) — the page may be JS-rendered or an "
            "error page"
        )
    lines: list[tuple[str, str]] = []
    for tag, raw in _BLOCK_RE.findall(match.group(1)):
        text = _strip_tags(raw)
        if not text:
            continue
        if text.startswith("Bildquelle:"):
            break  # ads / related teasers follow; body ends here
        if "bevorzugte Quelle bei Google" in text:
            continue  # Google-preferred-source prompt (+ its heading)
        if tag.lower() == "h2" and title and text == title:
            continue  # header subhead: the title again
        if tag.lower() == "p" and description and text == description:
            continue  # teaser paragraph: the description again
        if _PRICE_LINE_RE.match(text):
            continue  # bare price line from an ad block
        lines.append((tag.lower(), text))
    # An ad block's heading sits directly above the "Bildquelle:"
    # line ("Kleines Kraftwerk", "FOCUS+"): drop trailing orphan
    # subheads left behind by the truncation above — a real body
    # never ends with a bare subhead.
    while lines and lines[-1][0] == "h2":
        lines.pop()
    body = "\n\n".join(text for _, text in lines).strip()
    if not body:
        raise ValueError(
            "no article text found on this page (the <article> body is "
            "empty after filtering)"
        )
    return body


def _page_title(html_text: str) -> str:
    match = _TITLE_RE.search(html_text)
    if not match:
        return ""
    title = _strip_tags(match.group(1))
    return re.sub(r"\s*[-|]\s*FOCUS online\s*$", "", title, flags=re.I)


def parse_article(html_text: str) -> dict:
    """Extract the article from a focus.de page.

    Prefers the JSON-LD NewsArticle/Article "articleBody" — but
    FOCUS pages carry no articleBody, so in practice the body is
    always read from the server-rendered <article> paragraphs.
    Returns {title, description, body, author, published,
    word_count, teaser_only, paywalled, kind, video_url, duration}.
    Raises ValueError when no usable text is found.
    """
    blocks: list[dict] = []
    for match in _LD_JSON_RE.finditer(html_text):
        try:
            data = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            blocks.append(data)

    title = _page_title(html_text)
    description = ""
    og = _OG_DESC_RE.search(html_text)
    if og:
        description = html.unescape(og.group(1)).strip()

    for block in blocks:
        body = (block.get("articleBody") or "").strip()
        if not body:
            continue
        description = description or _strip_tags(str(block.get("description") or ""))
        return {
            "title": _strip_tags(str(block.get("headline") or "")) or title,
            "description": description,
            "body": body,
            "author": _author_name(block.get("author")),
            "published": str(block.get("datePublished") or "") or None,
            "word_count": len(body.split()),
            "teaser_only": bool(body) and body == description,
            "paywalled": not _is_free(block),
            "kind": "article",
            "video_url": None,
            "duration": None,
        }

    # A NewsArticle/Article block means the page IS an article — even
    # when it embeds a video (FOCUS article pages carry a VideoObject
    # block too, listed before the NewsArticle block). Only a page
    # with no article block at all is treated as a video page.
    article_block = None
    for block in blocks:
        if block.get("@type") in ("NewsArticle", "Article"):
            article_block = block
            break
    if article_block is not None:
        description = description or _strip_tags(
            str(article_block.get("description") or "")
        )
        headline = _strip_tags(str(article_block.get("headline") or "")) or title
        body = _ssr_body(html_text, title, description)
        paywalled = not _is_free(article_block)
        if not paywalled and _has_paywall_markers(html_text):
            # Defensive: a gated page shows only a stub body.
            if len(body.split()) < 100:
                paywalled = True
        if paywalled:
            body = description
        # Live-ticker pages ("... im Live-Ticker ...") carry no
        # article body in SSR: the entries load client-side and only
        # the latest entry's headline is in the server-rendered
        # page. Label them so callers are not misled by a tiny body.
        kind = (
            "live-ticker"
            if "live-ticker" in headline.casefold()
            or "live-ticker" in title.casefold()
            else "article"
        )
        return {
            "title": headline,
            "description": description,
            "body": body,
            "author": _author_name(article_block.get("author")),
            "published": (
                str(article_block.get("datePublished") or "") or None
            ),
            "word_count": len(body.split()),
            "teaser_only": bool(body) and body == description,
            "paywalled": paywalled,
            "kind": kind,
            "video_url": None,
            "duration": None,
        }

    for block in blocks:
        if block.get("@type") != "VideoObject":
            continue
        description = description or _strip_tags(str(block.get("description") or ""))
        return {
            "title": _strip_tags(str(block.get("name") or "")) or title,
            "description": description,
            "body": description,
            "author": "",
            "published": str(block.get("uploadDate") or "") or None,
            "word_count": len(description.split()),
            "teaser_only": True,
            "paywalled": not _is_free(block),
            "kind": "video",
            "video_url": str(block.get("contentUrl") or "") or None,
            "duration": str(block.get("duration") or "") or None,
        }

    body = _ssr_body(html_text, title, description)
    return {
        "title": title,
        "description": description,
        "body": body,
        "author": "",
        "published": None,
        "word_count": len(body.split()),
        "teaser_only": bool(body) and body == description,
        "paywalled": False,
        "kind": "article",
        "video_url": None,
        "duration": None,
    }


def search_items(items: list, query: str) -> list:
    """Case-insensitive substring match over title + kicker +
    description."""
    q = (query or "").strip().casefold()
    if not q:
        raise ValueError("query must not be empty")
    return [
        it for it in items
        if q in (it.get("title") or "").casefold()
        or q in (it.get("kicker") or "").casefold()
        or q in (it.get("description") or "").casefold()
    ]


def dedupe_sort(items: list) -> list:
    """De-duplicate by link, newest first (empty publish time sorts last)."""
    seen: set[str] = set()
    unique: list[dict] = []
    for it in items:
        if it["link"] in seen:
            continue
        seen.add(it["link"])
        unique.append(it)
    unique.sort(key=lambda it: it.get("published") or "", reverse=True)
    return unique
