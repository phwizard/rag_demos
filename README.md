# Zelensky Speeches Extract – Static + Dynamic

Two ways to host:

## Option A — **Dynamic** (quickest)
1. Put `dynamic/index.html` into any static host (GitHub Pages, Netlify, Vercel, Cloudflare Pages, Hugging Face Spaces).
2. URL will work immediately; it fetches rows live from the Hugging Face datasets-server.
   - **Requires your crawler to execute JavaScript** to see the `full_text` content.

## Option B — **Static (crawler-friendly)**
1. Run `python build.py --pages 1,2` locally (or let GitHub Actions do it).
2. It writes `docs/index.html` with all `full_text` baked in (no JS needed).
3. In GitHub repo settings: **Pages → Build from branch → main → /docs**.
4. Add `robots.txt` and `sitemap.xml` (edit domain placeholders).

### GitHub Actions (optional)
- The included workflow builds `docs/index.html` on every push. You can set a repo variable `PAGES` (e.g. `0,1,2,3`).

### Notes
- Each HF viewer page corresponds to 100 rows; `--pages 1,2` fetches rows 100–299.
- Dataset: `slava-medvedev/zelensky-speeches` (license: CC BY 4.0).
- If you need other datasets, edit `DATASET`, `CONFIG`, `SPLIT` in `build.py`.
