# focus-online-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/focus-online-mcp

سرور MCP غیررسمی و **فقط‌خواندنی** برای **[FOCUS online](https://www.focus.de)** — یکی از بزرگ‌ترین مجله‌های خبری آلمان — از طریق فید رسمی RSS (یک فید، حدود ۴۰۰ مورد، بدون کلید، بدون ورود) و صفحات مقالات که متن کامل آن‌ها از پاراگراف‌های `<article>` رندرشده در سرور خوانده می‌شود (`articleBody` در JSON-LD در صفحات FOCUS وجود ندارد). تیترهای برتر، اخبار بر اساس بخش (politik، kultur، panorama، sport، finanzen، earth و …)، فهرست بخش‌ها با تعداد موارد، جست‌وجوی کلیدواژه در کل فید و متن کامل مقالات. بدون کلید، بدون ورود.

> ساختهٔ محمد عباسی به‌عنوان بخشی از «کارخانهٔ MCP آلمان» (خط لولهٔ سبک سپهر). وابسته به FOCUS online یا Hubert Burda Media نیست.

## برای ایجنت‌های هوش مصنوعی

در پیکربندی کلاینت MCP اضافه کنید (stdio):

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

یا به‌صورت محلی اجرا کنید: `python -m focus_online_mcp.server` (نیازمند `mcp<2` و `httpx`).

## ابزارها

| ابزار | توضیح |
|------|-------------|
| `focus_headlines` | تیترهای برتر FOCUS online (فید رسمی RSS، حدود ۴۰۰ مورد)، جدیدترین اول — `limit` بین ۱ تا ۱۵۰. هر مورد شامل تیتر، kicker، لینک، تیزر، بخش، نویسنده، زمان انتشار و تصویر است |
| `focus_news_by_section` | تازه‌ترین اخبار یک بخش، فیلترشده از فید رسمی RSS — ‏`section`‏: مثلاً "politik" ،"kultur" ،"panorama" ،"sport" ،"finanzen" ،"earth" ،"gesundheit" ،"auto" ،"wissen" (فهرست امروز را با `focus_sections` ببینید)، ‏`limit`‏ بین ۱ تا ۱۵۰ |
| `focus_sections` | بخش‌های فید امروز با تعداد موارد هرکدام، از بیشترین به کمترین — از این نام‌ها در `focus_news_by_section` استفاده کنید |
| `focus_search_news` | جست‌وجوی اخبار با کلیدواژه (تیتر + kicker + تیزر) در کل فید رسمی RSS (حدود ۴۰۰ مورد) — ‏`query`‏ (مثلاً "Trump")، ‏`limit`‏ بین ۱ تا ۱۵۰ |
| `focus_get_article` | متن کامل یک صفحهٔ مقالهٔ FOCUS online (پاراگراف‌های `<article>` رندرشده در سرور) — ‏`url`‏: آدرس مقاله در www.focus.de (/<بخش>/<slug>_<uuid>.html) یا صفحهٔ خدماتی /rechner/. صفحات لایوتیکر `kind: "live-ticker"` برمی‌گردانند و فقط تیتر آخرین ورودی را دارند؛ صفحهٔ غیررایگان `paywalled: true` و فقط تیزر را برمی‌گرداند |
| `focus_health` | بررسی دسترسی (ok / blocked / error) — یک درخواست مؤدبانه |

نمونهٔ خروجی (`focus_headlines` با `limit` برابر ۲):

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

نکته‌ها:
- سرور **فید رسمی RSS** را می‌خواند (`https://www.focus.de/rss/`، حدود ۴۰۰ مورد، بررسی زنده در ۲۰۲۶-۱۱-۲۱). جست‌وجو و فیلتر بخش به‌صورت سمت‌کاربر روی فیدِ گرفته‌شده انجام می‌شود.
- فقط **یک فید** وجود دارد: فید جداگانه برای هر بخش وجود ندارد — آدرس `/rss/<بخش>/` برای همهٔ بخش‌های آزمایش‌شده ۴۰۴ می‌دهد (politik، wirtschaft، sport، kultur، digital، panorama، wissen، gesundheit، auto، reisen، geld) و `/rss/<بخش>.xml` با ۳۰۱ به فید اصلی برمی‌گردد. بخش‌ها از مسیر لینک هر مورد به دست می‌آیند (politik ‏۸۰‏، kultur ‏۸۰‏، panorama ‏۶۴‏، sport ‏۴۳‏، finanzen ‏۳۹‏، earth ‏۲۰‏ و … در فید ۲۰۲۶-۱۱-۲۱). فید هیچ برچسب `<category>` ندارد و `media:category` همیشه "news" است؛ `dc:creator` (نویسنده) در حدود ۵۷٪ موارد هست.
- **متن مقاله، صادقانه:** صفحات مقالهٔ FOCUS هیچ `articleBody` در JSON-LD ندارند، پس متن همیشه از پاراگراف‌های `<article>` رندرشده در سرور خوانده می‌شود (۵٬۸۶۷ نویسه در نمونهٔ مقالهٔ finanzen؛ سربرگ / تیزر / پیام «bevorzugte Quelle bei Google» حذف شده؛ همه‌چیز از اولین پاراگراف "Bildquelle:" به بعد — تبلیغات و مقالات مرتبط — بریده می‌شود). صفحات مقاله ممکن است ویدیو داشته باشند — صفحه‌ای که بلوک NewsArticle دارد همچنان مقاله محسوب می‌شود، نه صفحهٔ ویدیویی.
- **لایوتیکر:** صفحاتی با «... im Live-Ticker ...» در تیتر، هیچ متن ورودی در SSR ندارند — ورودی‌ها سمت‌کاربر بارگذاری می‌شوند. این صفحات `kind: "live-ticker"` برمی‌گردانند و فقط تیتر آخرین ورودی را دارند (۱۱ کلمه در نمونهٔ لایوتیکر جنگ اوکراین)، هرگز متن ساخته‌شده.
- **پی‌وال FOCUS+‎، صادقانه:** محتوای پولی وجود دارد (از مه ۲۰۲۵؛ مقالات Plus میان محتوای رایگان پخش می‌شوند) — اما نمونهٔ مقاله‌ای از بخش «Das Beste von FOCUS+» در صفحهٔ اصلی، متن کامل را سمت سرور برگرداند (۱۷ پاراگراف، ۴٬۷۰۲ نویسه)، پس هیچ نمونهٔ پولی‌ای برای اعتبارسنجی پیدا نشد. سرور `isAccessibleForFree: false` و نشانه‌های پی‌وال را هر وقت ظاهر شوند رعایت می‌کند و فقط `paywalled: true` با تیزر برمی‌گرداند.
- داده‌ها: فید عمومی RSS و صفحات مقالات FOCUS online — بدون کلید، بدون ورود، فقط‌خواندنی.

## توسعه

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — آفلاین، فید واقعی RSS و سه صفحهٔ مقالهٔ واقعی را تجزیه می‌کند (مقالهٔ NewsArticle در finanzen، مقالهٔ earth از «Das Beste von FOCUS+»، صفحهٔ خدماتی /rechner/ با VideoObject، و یک صفحهٔ لایوتیکر)
- `tests/test_live.py` — درخواست‌های محتاطانهٔ زنده به www.focus.de

تست‌ها: ۲۵ از ۲۵ سبز (۱۹ آفلاین + ۶ زنده، ۲۰۲۶-۱۱-۲۱).

## مجوز

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — رایگان برای استفادهٔ شخصی و غیرتجاری؛ استفادهٔ تجاری نیازمند مجوز جداگانه است (به LICENSE نگاه کنید).

---

ساختهٔ [محمد عباسی](https://github.com/mohammad-abbasi-sh) — [آلمانی‌باما](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
