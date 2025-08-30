#!/usr/bin/env python3
"""
Build a crawlable static site of Hugging Face dataset rows.

Features:
  1) Automatically iterates through all pages (keeps fetching until a page returns 0 rows).
  2) Writes one static HTML per page: docs/page-0001.html, page-0002.html, ...
  3) Generates docs/index.html with links to all subpages for easy crawling.
  4) Optionally emits sitemap.xml listing index + all pages when --base-url is provided.

Defaults target dataset: slava-medvedev/zelensky-speeches (config=default, split=train).

Examples
--------
# Build all pages (auto-detect) with 100 rows per page (HF viewer equivalent)
python build.py

# Different dataset / rows per page
python build.py --dataset myorg/mydataset --rows-per-page 200

# Emit sitemap with your public base URL
python build.py --base-url https://username.github.io/hf-zelensky-extract/
"""
import argparse, os, sys, json, html, time
from urllib.request import urlopen, Request
from urllib.parse import urlencode, urljoin

DATASET_DEFAULT = "slava-medvedev/zelensky-speeches"
CONFIG_DEFAULT = "default"
SPLIT_DEFAULT = "train"
ROWS_PER_PAGE_DEFAULT = 100
API = "https://datasets-server.huggingface.co/rows"

CSS = """
  body{margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif; background:#0f1220; color:#e8ecff}
  main{max-width:1100px;margin:0 auto;padding:20px} header{max-width:1100px;margin:0 auto;padding:16px 20px 0}
  h1{font-size:22px;margin:12px 0}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;margin:16px 0}
  article{background:#161a2b;border:1px solid #262a45;border-radius:16px;padding:16px;box-shadow:0 4px 14px rgba(0,0,0,.25)}
  h2{font-size:16px;margin:0 0 8px}
  .badges{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}
  .chip{display:inline-flex;align-items:center;gap:6px;background:#222642;border:1px solid #262a45;color:#9aa3c7;padding:4px 8px;border-radius:999px;font-size:12px}
  p{white-space:pre-wrap;margin:0;color:#e1e6ff;line-height:1.45}
  a{color:#6aa0ff;word-break:break-all;text-decoration:none}
  nav ul{display:flex;flex-wrap:wrap;gap:8px;list-style:none;padding:0}
  nav a.page{display:inline-block;padding:6px 10px;border-radius:10px;background:#222642;border:1px solid #262a45;text-decoration:none;color:#e8ecff;font-size:14px}
  footer{max-width:1100px;margin:0 auto;padding:16px 20px 40px;color:#9aa3c7}
"""

def ts_to_date(ts_like):
    if ts_like is None: return ""
    s = str(ts_like).replace(",", "")
    try:
        num = int(float(s))
        return time.strftime("%Y-%m-%d", time.gmtime(num))
    except Exception:
        return s

def fetch_rows(dataset, config, split, offset, length, user_agent="Mozilla/5.0 (Indexer)"):
    params = dict(dataset=dataset, config=config, split=split, offset=offset, length=length)
    url = f"{API}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": user_agent})
    with urlopen(req) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status} for {url}")
        data = json.loads(r.read().decode("utf-8"))
        rows = data.get("rows", [])
        return rows

def render_rows_to_html(rows):
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

def page_filename(page_idx):
    return f"page-{page_idx:04d}.html"

def write_page(dirpath, page_idx, title, inner_html, dataset_url):
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="index,follow">
  <title>{html.escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <div>Source: <a href="{dataset_url}">{dataset_url}</a></div>
  </header>
  <main>
    <section class="grid">
      {inner_html}
    </section>
  </main>
  <footer>License: CC BY 4.0. This page is static (no JS) for easy crawling.</footer>
</body>
</html>
"""
    out = os.path.join(dirpath, page_filename(page_idx))
    os.makedirs(dirpath, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return out

def write_index(dirpath, pages, title, dataset_url):
    # pages: list of (page_idx, count)
    links = []
    for idx, count in pages:
        fn = page_filename(idx)
        links.append(f'<li><a class="page" href="{fn}">Page {idx} <small>({count} rows)</small></a></li>')
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="index,follow">
  <title>{html.escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <div>Source: <a href="{dataset_url}">{dataset_url}</a></div>
  </header>
  <main>
    <nav>
      <ul>
        {''.join(links) if links else '<li>No pages found.</li>'}
      </ul>
    </nav>
  </main>
  <footer>License: CC BY 4.0. This index links to static subpages for easy crawling.</footer>
</body>
</html>
"""
    out = os.path.join(dirpath, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return out

def write_sitemap(dirpath, base_url, pages):
    if not base_url:
        return None
    def join(u, p):
        if not u.endswith("/"):
            u = u + "/"
        return urljoin(u, p)
    urls = [join(base_url, "index.html")] + [join(base_url, page_filename(idx)) for idx, _ in pages]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lines.append(f"  <url><loc>{html.escape(u)}</loc></url>")
    lines.append("</urlset>")
    out = os.path.join(dirpath, "sitemap.xml")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=DATASET_DEFAULT)
    ap.add_argument("--config", default=CONFIG_DEFAULT)
    ap.add_argument("--split", default=SPLIT_DEFAULT)
    ap.add_argument("--rows-per-page", type=int, default=ROWS_PER_PAGE_DEFAULT)
    ap.add_argument("--outdir", default="docs")
    ap.add_argument("--base-url", default="", help="Public base URL for sitemap (e.g., https://user.github.io/repo/)")
    args = ap.parse_args()

    dataset_url = f"https://huggingface.co/datasets/{args.dataset}"
    os.makedirs(args.outdir, exist_ok=True)

    # Iterate pages until empty
    pages_meta = []  # list of (page_idx, count)
    page_idx = 1
    offset = 0
    while True:
        print(f"Fetching page {page_idx} (offset={offset})…")
        rows = fetch_rows(args.dataset, args.config, args.split, offset, args.rows_per_page)
        if not rows:
            print("No more rows. Stopping.")
            break
        inner = render_rows_to_html(rows)
        write_page(args.outdir, page_idx, f"{args.dataset} – page {page_idx}", inner, dataset_url)
        pages_meta.append((page_idx, len(rows)))
        page_idx += 1
        offset += args.rows_per_page

    # Write index and optional sitemap
    write_index(args.outdir, pages_meta, f"{args.dataset} – index", dataset_url)
    if args.base_url:
        write_sitemap(args.outdir, args.base_url, pages_meta)

    print(f"Done. Wrote {len(pages_meta)} page(s) + index.html into {args.outdir}/")

if __name__ == "__main__":
    main()
