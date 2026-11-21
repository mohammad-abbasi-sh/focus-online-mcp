"""HTTP layer for focus_online_mcp — plain httpx GETs against
www.focus.de.

Endpoints, all public, no key, no login:
- the official RSS feed: https://www.focus.de/rss/ (one feed,
  ~400 items; per-section feeds do not exist — /rss/<section>/
  404s and /rss/<section>.xml 301-redirects to the main feed,
  verified 2026-11-21)
- article pages: https://www.focus.de/<section>/<slug>_<uuid>.html
  (also _id_<digits>.html and /rechner/... URLs) — the full text
  is read from the server-rendered <article> paragraphs (the
  JSON-LD articleBody is absent on FOCUS pages); see
  domain.parse_article.

Only www.focus.de is ever fetched.
"""
from __future__ import annotations

import os
import ssl
import time
from urllib.parse import urlparse

import httpx

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = 25.0
ALLOWED_HOSTS = ("www.focus.de",)
HEALTH_URL = "https://www.focus.de/rss/"
FEED_URL = "https://www.focus.de/rss/"


class FocusError(RuntimeError):
    pass


def _verify():
    """TLS trust store: the OS bundle when present, else httpx/certifi.

    The OS bundle matters behind MITM egress proxies (their CA is in the
    system store, not in certifi) and is the right default on Linux
    anyway; on systems without it we fall back to certifi.
    """
    for path in (
        "/etc/ssl/certs/ca-certificates.crt",
        ssl.get_default_verify_paths().openssl_cafile,
    ):
        if path and os.path.exists(path):
            return ssl.create_default_context(cafile=path)
    return True


def _client(accept: str) -> httpx.Client:
    # NOTE: we read the proxy URL from the environment but never log it.
    # trust_env=False because httpx fails to parse bracketed IPv6 entries
    # (e.g. [::1]) that some environments put in no_proxy.
    proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    return httpx.Client(
        headers={"User-Agent": UA, "Accept": accept},
        timeout=TIMEOUT,
        proxy=proxy or None,
        trust_env=False,
        verify=_verify(),
        follow_redirects=True,
    )


def _check_host(url: str) -> None:
    host = (urlparse(url).netloc or "").lower()
    if host not in ALLOWED_HOSTS:
        raise FocusError(
            f"only {', '.join(ALLOWED_HOSTS)} pages are fetched "
            f"(got {host or url!r})"
        )


def _get(url: str, accept: str) -> str:
    """GET with one retry on 429/5xx and on transient network errors."""
    _check_host(url)
    last_exc: Exception | None = None
    r: httpx.Response | None = None
    for attempt in range(2):
        try:
            with _client(accept) as c:
                r = c.get(url)
        except httpx.HTTPError as e:
            last_exc = e
            if attempt == 0:
                time.sleep(1.0)
                continue
            raise FocusError(f"network error fetching {url}: {e}") from e
        if r.status_code in (429, 500, 502, 503):
            if attempt == 0:
                time.sleep(1.0)
                continue
        break
    assert r is not None  # loop always assigns r or raises
    if r.status_code == 403:
        raise FocusError(
            f"www.focus.de returned HTTP 403 for {url} (bot wall) — try again later"
        )
    if r.status_code == 429:
        raise FocusError(
            "www.focus.de rate-limited the request (HTTP 429) — try again later"
        )
    if r.status_code != 200:
        raise FocusError(f"www.focus.de returned HTTP {r.status_code} for {url}")
    return r.text


def fetch_feed(url: str) -> str:
    """GET the official FOCUS online RSS feed; returns the raw XML text."""
    if url.rstrip("/") != FEED_URL.rstrip("/"):
        raise FocusError(
            f"only the official FOCUS online RSS feed is fetched "
            f"(got {url!r})"
        )
    return _get(url, "application/rss+xml, application/xml, text/xml, */*")


def fetch_article(url: str) -> str:
    """GET one www.focus.de article page; returns the raw HTML text.

    Article URLs are /<section>/<slug>_<uuid>.html (also
    _id_<digits>.html and /rechner/... pages). URLs with a fragment
    are refused, as are non-.html paths (feed URLs, section pages,
    the /focusplus/ hub).
    """
    parsed = urlparse(url)
    if parsed.fragment:
        raise FocusError(
            "URLs with a fragment are not articles "
            f"(got {url!r})"
        )
    path = parsed.path
    if not path.endswith(".html"):
        raise FocusError(
            "only www.focus.de article URLs (pages ending in .html) "
            f"are fetched (got {url!r})"
        )
    return _get(url, "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")


def health_check() -> dict:
    """One polite probe of the source feed.

    Returns {"status": "ok"|"blocked"|"error", "http_status": int|None,
    "url": ..., "detail": ...}. Used by the `focus_health` tool
    and the daily smoke CI.
    """
    url = HEALTH_URL
    try:
        fetch_feed(url)
    except FocusError as e:
        msg = str(e)
        if "403" in msg:
            return {"status": "blocked", "http_status": 403, "url": url, "detail": msg}
        if "429" in msg:
            return {"status": "blocked", "http_status": 429, "url": url, "detail": msg}
        return {"status": "error", "http_status": None, "url": url, "detail": msg}
    return {"status": "ok", "http_status": 200, "url": url}
