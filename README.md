# focus-online-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/focus-online-mcp

Unofficial **read-only** MCP server for **[FOCUS online](https://www.focus.de)** — one of Germany's biggest news magazines — via its official RSS feed (one feed, ~400 items, no key, no login) and article pages, whose full text is read from the server-rendered `<article>` paragraphs (the JSON-LD `articleBody` is absent on FOCUS pages). Top headlines, news by section (politik, kultur, panorama, sport, finanzen, earth, ...), a section overview with item counts, keyword search across the whole feed, and full article text. No key, no login.

> Built by Mohammad Abbasi as part of the "Germany MCP factory" (Sepehr-style pipeline). Not affiliated with FOCUS online or Hubert Burda Media.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "focus-online": {
      "command": "uvx",
      "args": ["focus-online-mcp==0.1.0"]
    }
  }
}
```

Or run locally: `python -m focus_online_mcp.server` (needs `mcp<2`, `httpx`).

## Tools

| Tool | Description |
|------|-------------|
| `focus_headlines` | Top FOCUS online headlines (official RSS feed, ~400 items), newest first — `limit` 1..150. Items carry title, kicker, link, teaser, section, author, publish time and image |
| `focus_news_by_section` | Newest news of one section, filtered from the official RSS feed — `section`: e.g. "politik", "kultur", "panorama", "sport", "finanzen", "earth", "gesundheit", "auto", "wissen" (see `focus_sections` for today's list), `limit` 1..150 |
| `focus_sections` | Sections in today's feed with their item counts, most items first — use these names with `focus_news_by_section` |
| `focus_search_news` | Search news by keyword (title + kicker + teaser) across the whole official RSS feed (~400 items) — `query` (e.g. "Trump"), `limit` 1..150 |
| `focus_get_article` | Full text of one FOCUS online article page (server-rendered `<article>` paragraphs) — `url`: a www.focus.de article URL (/<section>/<slug>_<uuid>.html) or a /rechner/ service page. Live-ticker pages return `kind: "live-ticker"` with only the latest entry's headline; a non-free page returns `paywalled: true` with the teaser only |
| `focus_health` | Reachability probe (ok / blocked / error) — one polite request |

Example output (`focus_headlines`, `limit` 2):

```json
{"feed_title": "FOCUS online - Aktuelle Nachrichten", "total_results": 400, "count": 2,
 "items": [
  {"title": "Vom Boom zum Absturz: Die Trump-Wette geht nicht mehr auf",
   "kicker": "Milliardenverluste für Anleger",
   "link": "https://www.focus.de/finanzen/vom-boom-zum-absturz-die-trump-wette-geht-nicht-mehr-auf_3f006815-3ea2-4d90-9562-653aad882a67.html",
   "description": "Donald Trumps geschätztes Vermögen ist seit September 2025 um eine Milliarde US-Dollar geschrumpft. ...",
   "section": "finanzen", "author": "Ansgar Graw",
   "published": "2026-11-21T10:09:00+00:00",
   "image_url": "https://quadro.burda-forward.de/ctf/94113456-f5dc-4ba3-a690-caadb809e1f2.5a8a4596-8fc0-4a9d-bdf7-db1a81c2ea77.jpeg?..."},
  ...]}
```

Notes:
- The server reads the **official RSS feed** (`https://www.focus.de/rss/`, ~400 items, verified live 2026-11-21). Search and section filtering run client-side over the fetched feed.
- There is **only one feed**: per-section feeds do not exist — `/rss/<section>/` 404s for every section tried (politik, wirtschaft, sport, kultur, digital, panorama, wissen, gesundheit, auto, reisen, geld) and `/rss/<section>.xml` 301-redirects to the main feed. Sections are derived from each item's link path (politik 80, kultur 80, panorama 64, sport 43, finanzen 39, earth 20, ... in the 2026-11-21 feed). The feed carries no `<category>` tags and `media:category` is always "news"; `dc:creator` (the author) is present on ~57% of items.
- **Article text, honestly:** FOCUS article pages carry NO JSON-LD `articleBody`, so the body is always read from the server-rendered `<article>` paragraphs (5,867 chars sampled on a finanzen article; header / teaser / "bevorzugte Quelle bei Google" prompt filtered out; everything from the first "Bildquelle:" paragraph on — ads and related-article teasers — cut). Article pages may embed a video — a page with a NewsArticle block is still treated as an article, never as a video page.
- **Live tickers:** pages titled "... im Live-Ticker ..." carry no entry text in SSR — the entries load client-side. They return `kind: "live-ticker"` with only the latest entry's headline (11 words sampled on the Ukraine-Krieg ticker), never a fabricated body.
- **FOCUS+ paywall, honestly:** paid content exists (launched May 2025; Plus articles are mixed into the free content) — but the one sampled article from the homepage's "Das Beste von FOCUS+" shelf returned its FULL text server-side (17 paragraphs, 4,702 chars), so no paywalled sample could be validated. The server honours `isAccessibleForFree: false` and paywall markers when they appear, returning `paywalled: true` with the teaser only.
- Data: FOCUS online public RSS feed and article pages — no key, no login, read-only.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parses the real captured RSS feed plus three real article pages (finanzen NewsArticle, a "Das Beste von FOCUS+" earth article, a /rechner/ service page with an embedded VideoObject, and a live-ticker page)
- `tests/test_live.py` — cautious live requests against www.focus.de

Tests: 25/25 green (19 offline + 6 live, 2026-11-21).

## License

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — free for personal and non-commercial use; commercial use needs a separate license (see LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
