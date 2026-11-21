# focus-online-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/focus-online-mcp

Inoffizieller **Read-only**-MCP-Server für **[FOCUS online](https://www.focus.de)** — eines der größten Nachrichtenmagazine Deutschlands — über den offiziellen RSS-Feed (ein Feed, ~400 Einträge, kein Schlüssel, kein Login) und Artikelseiten, deren Volltext aus den serverseitig gerenderten `<article>`-Absätzen gelesen wird (das JSON-LD-`articleBody` fehlt auf FOCUS-Seiten). Top-Schlagzeilen, Nachrichten nach Ressort (politik, kultur, panorama, sport, finanzen, earth, …), eine Ressort-Übersicht mit Eintragszahlen, Stichwortsuche über den ganzen Feed und Volltexte von Artikeln. Kein Schlüssel, kein Login.

> Gebaut von Mohammad Abbasi als Teil der "Germany MCP factory" (Sepehr-ähnliche Pipeline). Nicht mit FOCUS online oder Hubert Burda Media verbunden.

## Für KI-Agenten

In die MCP-Client-Konfiguration eintragen (stdio):

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

Oder lokal starten: `python -m focus_online_mcp.server` (benötigt `mcp<2`, `httpx`).

## Tools

| Tool | Beschreibung |
|------|-------------|
| `focus_headlines` | Top-Schlagzeilen von FOCUS online (offizieller RSS-Feed, ~400 Einträge), neueste zuerst — `limit` 1..150. Einträge tragen Titel, Kicker, Link, Teaser, Ressort, Autor, Veröffentlichungszeit und Bild |
| `focus_news_by_section` | Neueste Nachrichten eines Ressorts, gefiltert aus dem offiziellen RSS-Feed — `section`: z. B. "politik", "kultur", "panorama", "sport", "finanzen", "earth", "gesundheit", "auto", "wissen" (siehe `focus_sections` für die heutige Liste), `limit` 1..150 |
| `focus_sections` | Ressorts im heutigen Feed mit ihren Eintragszahlen, nach Anzahl sortiert — diese Namen mit `focus_news_by_section` verwenden |
| `focus_search_news` | Stichwortsuche in den Nachrichten (Titel + Kicker + Teaser) über den ganzen offiziellen RSS-Feed (~400 Einträge) — `query` (z. B. "Trump"), `limit` 1..150 |
| `focus_get_article` | Volltext einer FOCUS-online-Artikelseite (serverseitig gerenderte `<article>`-Absätze) — `url`: eine www.focus.de-Artikel-URL (/<ressort>/<slug>_<uuid>.html) oder eine /rechner/-Service-Seite. Live-Ticker-Seiten liefern `kind: "live-ticker"` mit nur der neuesten Eintrags-Schlagzeile; eine nicht frei zugängliche Seite liefert `paywalled: true` und nur den Teaser |
| `focus_health` | Erreichbarkeitsprüfung (ok / blocked / error) — eine höfliche Anfrage |

Beispielausgabe (`focus_headlines`, `limit` 2):

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

Hinweise:
- Der Server liest den **offiziellen RSS-Feed** (`https://www.focus.de/rss/`, ~400 Einträge, live verifiziert 2026-11-21). Suche und Ressort-Filter laufen clientseitig über den geladenen Feed.
- Es gibt **nur einen Feed**: Ressort-Feeds existieren nicht — `/rss/<ressort>/` liefert 404 für jedes probierte Ressort (politik, wirtschaft, sport, kultur, digital, panorama, wissen, gesundheit, auto, reisen, geld) und `/rss/<ressort>.xml` leitet per 301 auf den Haupt-Feed weiter. Ressorts werden aus dem Link-Pfad jedes Eintrags abgeleitet (politik 80, kultur 80, panorama 64, sport 43, finanzen 39, earth 20, … im Feed vom 2026-11-21). Der Feed trägt keine `<category>`-Tags und `media:category` ist immer "news"; `dc:creator` (der Autor) ist bei ~57 % der Einträge vorhanden.
- **Artikeltexte, ehrlich:** FOCUS-Artikelseiten tragen KEIN JSON-LD-`articleBody`, der Text wird daher immer aus den serverseitig gerenderten `<article>`-Absätzen gelesen (5.867 Zeichen in der Stichprobe eines finanzen-Artikels; Kopf- / Teaser- / "bevorzugte Quelle bei Google"-Hinweis herausgefiltert; alles ab dem ersten "Bildquelle:"-Absatz — Werbung und verwandte Artikel — abgeschnitten). Artikelseiten können ein Video einbetten — eine Seite mit NewsArticle-Block gilt trotzdem als Artikel, nie als Videoseite.
- **Live-Ticker:** Seiten mit "... im Live-Ticker ..." im Titel tragen keinen Eintragstext im SSR — die Einträge laden clientseitig. Sie liefern `kind: "live-ticker"` mit nur der neuesten Eintrags-Schlagzeile (11 Wörter in der Stichprobe des Ukraine-Krieg-Tickers), nie einen erfundenen Text.
- **FOCUS+-Paywall, ehrlich:** Bezahlinhalte existieren (gestartet Mai 2025; Plus-Artikel werden unter die kostenlosen Inhalte gemischt) — aber der eine Stichproben-Artikel aus der Startseiten-Rubrik "Das Beste von FOCUS+" lieferte seinen VOLLEN Text serverseitig (17 Absätze, 4.702 Zeichen), sodass keine Paywall-Stichprobe validiert werden konnte. Der Server respektiert `isAccessibleForFree: false` und Paywall-Markierungen, sobald sie auftreten, und liefert dann `paywalled: true` und nur den Teaser.
- Daten: öffentlicher FOCUS-online-RSS-Feed und Artikelseiten — kein Schlüssel, kein Login, nur lesend.

## Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parst den echten, gespeicherten RSS-Feed sowie drei echte Artikelseiten (finanzen-NewsArticle, ein "Das Beste von FOCUS+"-earth-Artikel, eine /rechner/-Service-Seite mit eingebettetem VideoObject, und eine Live-Ticker-Seite)
- `tests/test_live.py` — vorsichtige Live-Anfragen an www.focus.de

Tests: 25/25 grün (19 offline + 6 live, 2026-11-21).

## Lizenz

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — frei für private und nicht-kommerzielle Nutzung; kommerzielle Nutzung braucht eine separate Lizenz (siehe LICENSE).

---

Gebaut von [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
