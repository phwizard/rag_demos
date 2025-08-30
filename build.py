#!/usr/bin/env python3
"""
Builds a fully static HTML page with Zelensky speeches `full_text` chunks baked in,
so any crawler can index without executing JavaScript.

Usage:
  python build.py --pages 1,2  (defaults to 1,2)
Outputs to ./docs/index.html (GitHub Pages friendly if you serve from /docs)
"""
import argparse, os, sys, json, html, time
from urllib.request import urlopen
from urllib.parse import urlencode

DATASET = "slava-medvedev/zelensky-speeches"
CONFIG = "default"
SPLIT = "train"
ROWS_PER_PAGE = 100
API = "https://datasets-server.huggingface.co/rows"

def fetch_page(page:int):
    params = {
        "dataset": DATASET,
        "config": CONFIG,
        "split": SPLIT,
        "offset": page * ROWS_PER_PAGE,
        "length": ROWS_PER_PAGE,
    }
    url = f"{API}?{urlencode(params)}"
    with urlopen(url) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status} for {url}")
        return json.loads(r.read().decode("utf-8"))

def ts_to_date(ts_like):
    if ts_like is None: return ""
    s = str(ts_like).replace(",", "")
    try:
        num = int(float(s))
        return time.strftime("%Y-%m-%d", time.gmtime(num))
    except Exception:
        return s

def render(rows):
    # minimalist, crawlable HTML
    parts = []
    for item in rows:
        r = item.get("row", {})
        topic = html.escape(str(r.get("topic","(untitled)")))
        lang = html.escape(str(r.get("lang","")).upper())
        date = html.escape(ts_to_date(r.get("date")))
        full_text = html.escape(str(r.get("full_text","")))
        link = html.escape(str(r.get("link","")))
        article = f"""
<article>
  <h2>{topic}</h2>
  <div class="badges"><span class="chip">{lang}</span> <span class="chip">{date}</span></div>
  <p>{full_text}</p>
  {f'<div class="source"><a href="{link}">{link}</a></div>' if link else ''}
</article>
"""
        parts.append(article)
    return "\n".join(parts)

def make_html(content, page_list):
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="index,follow">
  <title>Zelensky Speeches – static extract (pages {','.join(map(str,page_list))})</title>
  <style>
    body{{margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif; background:#0f1220; color:#e8ecff}}
    main{{max-width:1100px;margin:0 auto;padding:20px}} header{{max-width:1100px;margin:0 auto;padding:16px 20px 0}}
    h1{{font-size:22px;margin:12px 0}} .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;margin:16px 0}}
    article{{background:#161a2b;border:1px solid #262a45;border-radius:16px;padding:16px;box-shadow:0 4px 14px rgba(0,0,0,.25)}}
    h2{{font-size:16px;margin:0 0 8px}} .badges{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}}
    .chip{{display:inline-flex;align-items:center;gap:6px;background:#222642;border:1px solid #262a45;color:#9aa3c7;padding:4px 8px;border-radius:999px;font-size:12px}}
    p{{white-space:pre-wrap;margin:0;color:#e1e6ff;line-height:1.45}} a{{color:#6aa0ff;word-break:break-all;text-decoration:none}}
    footer{{max-width:1100px;margin:0 auto;padding:16px 20px 40px;color:#9aa3c7}}
  </style>
</head>
<body>
  <header>
    <h1>Zelensky speeches · static extract</h1>
    <div>Pages: {', '.join(map(str,page_list))}. Source: <a href="https://huggingface.co/datasets/slava-medvedev/zelensky-speeches">slava-medvedev/zelensky-speeches</a></div>
  </header>
  <main>
    <section class="grid">
      {content}
    </section>
  </main>
  <footer>License: CC BY 4.0. This page is fully static for easy crawling.</footer>
</body>
</html>
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="1,2", help="Comma-separated HF viewer page numbers (each = 100 rows)")
    ap.add_argument("--out", default="docs/index.html", help="Output HTML path")
    args = ap.parse_args()
    pages = [int(x.strip()) for x in args.pages.split(",") if x.strip().isdigit()]
    rows = []
    for p in pages:
        print(f"Fetching page {p}…")
        data = fetch_page(p)
        rows.extend(data.get("rows", []))
    html_doc = make_html(render(rows), pages)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"Wrote {args.out} with {len(rows)} rows.")

if __name__ == "__main__":
    main()
