# 🗂️ Project Requirements Document (PRD)

## 📛 Project Title

**County Health Explorer**

## 🎯 Purpose

Build a minimalist, reproducible, full-stack spatial data science application to explore U.S. county-level health data. This project will showcase backend-to-frontend integration using DuckDB, FastAPI, and vanilla JavaScript with Observable Plot for cartographically accurate mapping and statistical charting.

## 🧱 Stack Overview

### Backend:

* **Language**: Python 3.10+
* **Framework**: FastAPI
* **Database**: DuckDB (with spatial extension)
* **Spatial Libs**: GeoPandas, PySAL

### Frontend:

* **Language**: Vanilla JavaScript (ES6)
* **Mapping & Charts**: Observable Plot (UMD) with D3 projections
* **Projections**: Albers Equal Area for accurate spatial representation
* **UI**: Plain HTML/CSS (no Tailwind or JS frameworks)

## 📁 Directory Structure

```
county-health-explorer/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── etl.py
│   │   └── routes/
│   │       ├── api.py
│   │       └── tiles.py
│   ├── templates/
│   └── tests/
├── frontend/
│   ├── css/
│   ├── js/
│   └── index.html
├── data/
├── scripts/
│   ├── etl.sh
│   └── dev.sh
└── README.md
```

## 🧪 Functional Requirements

### 🐍 Backend

1. **ETL Pipeline**

   * Load `county_health.csv` into DuckDB
   * Normalize column names
   * Join county GeoJSON to CSV via `fips_code`
   * Create spatial WKB view
   * Validate ETL output (e.g., 3142 counties, no nulls, valid ranges)

2. **API Endpoints**

   * `GET /api/vars`: List of available variables and metadata
   * `GET /api/variables/categories`: Grouped by health domain
   * `GET /api/choropleth?var=<variable>`: Return GeoJSON with joined data and class breaks
   * `GET /api/stats?var=<variable>`: Summary stats (count, mean, std, min, max)
   * `GET /api/moran?var=<variable>`: Moran's I spatial stat
   * `GET /api/corr?vars=var1,var2`: Correlation between variables
   * `GET /api/counties/{fips}`: Individual county details
   * `GET /api/neighbors/{fips}`: Spatial neighbors for local analysis

3. **Sample API Responses**

```json
// GET /api/stats?var=premature_death
{
  "variable": "premature_death",
  "count": 3142,
  "mean": 7605.2,
  "std": 1212.3,
  "min": 4321,
  "max": 10234
}

// GET /api/corr?vars=smoking,obesity
{
  "var1": "smoking",
  "var2": "obesity",
  "correlation": 0.67
}

// GET /api/choropleth?var=obesity
{
  "type": "FeatureCollection",
  "features": [
    { "type": "Feature", "properties": {"fips": "08031", "value": 24.3, "class": 5 }, "geometry": { ... } },
    ...
  ]
}
```

4. **Error Handling Requirements**

* All API errors return JSON in the format:

```json
{
  "error": "Invalid variable name",
  "status": 400,
  "details": "Variable 'foobar' not found in dataset"
}
```

* 400: Bad Request — malformed or invalid query param
* 404: Not Found — FIPS code or variable not found
* 500: Internal Server Error — fallback for uncaught exceptions
* All exceptions should be logged with timestamps and request context

### 🖥️ Frontend

1. **Landing Page (index.html)**

   * Loads Observable Plot map with Albers Equal Area projection and default choropleth (e.g., "Premature Death")
   * Sidebar with `<select>` dropdown for variable
   * Panels for stats, charts (histogram, scatter), legend

2. **Interactivity & State Management**

   * Central `AppState` JS object:

```javascript
const AppState = {
  currentVariable: 'premature_death',
  selectedCounty: null,
  mapLoaded: false,
  projection: 'albers-usa' // Albers Equal Area projection
};
```

* Map updates dynamically on variable change
* JS fetches `/api/choropleth`, updates Observable Plot map and legend
* Observable Plot renders both maps and charts in `<svg>` elements

3. **Progressive Enhancement**

   * Site degrades gracefully without JS
   * CSS provides baseline styles for mobile/desktop

## 🧪 Testing Strategy

### Guiding Principles

* **Test the arteries, not the capillaries**: Data integrity and stats drive insight; presentation is inspected manually
* **Fail loudly, early, and locally**: ETL or API regressions should break CI within seconds
* **Write tests where AI agents are weakest**: Deterministic outputs (ETL, PySAL) deserve assertions; Observable Plot doesn't

### Test Scope Matrix

| Layer                   | Test? | Rationale                                                         |
| ----------------------- | ----- | ----------------------------------------------------------------- |
| **ETL Pipeline**        | ✅     | Source of truth; must load 3,142 counties, join, validate ranges |
| **API Endpoints**       | ✅     | Contract for frontend + third‑party clients                      |
| **Spatial Stats**       | ✅     | Easy to mis‑code; deterministic checks                           |
| Observable Plot DOM     | ❌     | Visual layer; manual/visual QA sufficient                        |
| CSS / Styling           | ❌     | Style guide + browser testing covers it                          |

### Critical Test Areas

1. **ETL Integrity**: County count (3,142), FIPS uniqueness, geometry validation
2. **API Contracts**: Endpoint responses, error handling, data formats
3. **Spatial Statistics**: Moran's I bounds, correlation calculations

**📋 Full Testing Strategy**: See [testing-strategy.md](testing-strategy.md) for complete test specifications, tooling, and execution details.

### Success Metrics

* **Green CI** on every PR within < 60 seconds
* **≥15 targeted tests** covering ETL, API contracts, stats  
* **0 silent data‑integrity bugs** in production after launch

## 🚀 Stretch Goals

### ✅ Definitely Do:

* **Custom Projections**: Experiment with different D3 projections for regional focus
* **Client-side Filtering**: Use DuckDB-WASM in-browser for lightweight querying

### ⚠️ Maybe Skip:

* **Time-series Support**: Too complex for MVP
* **Overlay Layers**: Risk of scope creep

## 🛠️ Non-Functional Requirements

* Runs without Docker or build tools
* Zero external JS frameworks
* Hot-reload dev mode via `uvicorn`
* Fully reproducible ETL with fixed seeds
* Minimal dependencies

## ✅ Success Metrics

### Code Quality

* All API endpoints documented via OpenAPI
* ETL is idempotent and testable
* Tests pass and cover core logic

### UX

* Map interactions < 100ms
* Mobile-friendly layout
* Accessible choropleth color palettes
* Cartographically accurate projections (no web mercator distortion)
* Frontend functions in no-JS environments

## 📈 KPIs for MVP

* Time-to-First-Map: <2s
* API latency: <150ms
* DuckDB file size: <50MB
* Codebase <2,000 LOC

## 📅 Timeline (1-week sprints)

| Week | Deliverable                          |
| ---- | ------------------------------------ |
| 1    | ETL pipeline + hardcoded map page    |
| 2    | API endpoints + variable browser     |
| 3    | Choropleth + Observable Plot integration with Albers projection |
| 4    | Stats + Observable Plot charts       |
| 5    | Test coverage + accessibility polish |

## ✍️ Authors

* Richard Donohue (GIS & AI consultant)
* Bruce (AI collaborator)

## 📚 Data Source

* County Health Rankings 2025 (CSV)
* US Census TIGER/CartoDB counties (GeoJSON, 1:5m scale)

---

> "Simplicity is an antidote to confusion; when the mind is clear, action is precise."

This PRD is designed for **agentic development**, **repeatable science**, and **public-serving clarity**. Build what works. Deploy what lasts.
