# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask-based sales analytics dashboard for chocolate products. The app loads CSV data into a merged Pandas DataFrame at startup and serves pre-computed aggregations to a Chart.js frontend.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (dev server on http://localhost:5000)
python app.py

# Run production server (as deployed on Render)
gunicorn app:app
```

## Architecture

### Data → API → Frontend flow

1. **Startup**: `app.py` loads all four CSVs (`shipments.csv`, `people.csv`, `geo.csv`, `products.csv`) into a single merged Pandas DataFrame (`DF`) held in memory. Multiple left-joins are applied; post-merge column conflicts (e.g., `Geo_y`, `Product_y`) are resolved by renaming.

2. **API layer** (`app.py`): ~11 Flask routes perform Pandas aggregations on `DF` on request and return JSON. Key routes:
   - `/api/summary` — overall KPIs
   - `/api/drilldown` — detail breakdown triggered by chart-element clicks (date-grouped)
   - `/api/revenue-by-*` and `/api/top-*` — chart data feeds

3. **Frontend** (`templates/`): Two HTML pages with inline JavaScript.
   - `landing.html` — animated constellation canvas background, KPI preview cards, mini bar chart, CTA to dashboard
   - `dashboard.html` — 5 KPI cards + 8 Chart.js charts; each chart fetches its own `/api/*` endpoint via `fetch()`; supports drill-down popup on chart-element click
   - `index.html` — redirect to landing page

### Key structural notes

- There is **no database** — all data lives in CSV files under `data/`.
- The merged `DF` is a **module-level global** in `app.py`; all route handlers read from it directly.
- Chart.js 4.4.1 is loaded from CDN; no frontend build step exists.
- Deployment target is **Render** (see `render.yaml`; PORT env var = 10000).
