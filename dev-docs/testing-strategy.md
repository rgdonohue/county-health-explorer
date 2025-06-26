# 🧪 HealthViz Testing Strategy (v1.0)

This guide defines *where* and *why* we test HealthViz, balancing confidence with minimal overhead. It synthesises team feedback and pragmatic best‑practices.

---

## 1 Guiding Principles

1. **Test the arteries, not the capillaries**: Data integrity and stats drive insight; presentation is inspected manually.
2. **Fail loudly, early, and locally**: ETL or API regressions should break CI within seconds.
3. **Write tests where AI agents are weakest**: Deterministic outputs (ETL, PySAL) deserve assertions; Observable Plot doesn’t.
4. **Keep fixtures tiny**: Use micro‑CSV/GeoJSON slices for speed.

---

## 2 Test Scope Matrix

| Layer                   | Test? | Rationale                                                         |
| ----------------------- | ----- | ----------------------------------------------------------------- |
| **ETL Pipeline**        | ✅     | Source of truth; must load 3 142 counties, join, validate ranges. |
| **API Endpoints**       | ✅     | Contract for frontend + third‑party clients.                      |
| **Spatial Stats**       | ✅     | Easy to mis‑code; deterministic checks.                           |
| Observable Plot DOM     | ❌     | Visual layer; manual/visual QA sufficient.                        |
| CSS / Styling           | ❌     | Style guide + browser testing covers it.                          |
| DuckDB CRUD (adhoc SQL) | ❌     | Covered implicitly by ETL & analytics tests.                      |

---

## 3 Directory Layout

```text
backend/
└─ tests/
   ├─ conftest.py       # fixtures (DuckDB test db, FastAPI client)
   ├─ test_etl.py       # data pipeline integrity
   ├─ test_api.py       # endpoint smoke + edge cases
   └─ test_analysis.py  # Moran’s I, correlation, quantile bins
```

---

## 4 Critical Test Specs

### 4.1 ETL Integrity

```python
# test_etl.py

def test_county_count():
    df = run_etl_pipeline()
    assert df.shape[0] == 3142

def test_fips_uniqueness(df_etl):
    assert df_etl['fips'].nunique() == 3142
```

*Additional checks*: null geometry, numeric ranges, CRS validity.

### 4.2 API Contracts

```python
# test_api.py

def test_choropleth_endpoint(client):
    r = client.get('/api/choropleth?var=premature_death')
    assert r.status_code == 200
    geo = r.json()
    assert geo['type'] == 'FeatureCollection'
    assert len(geo['features']) == 3142
```

Include 400 & 404 cases.

### 4.3 Spatial Statistics

```python
# test_analysis.py

def test_morans_i_bounds():
    I = morans_i(sample_values, w_matrix)
    assert -1 <= I <= 1
```

Edge‑case fixtures: zero variance, perfect clustering.

---

## 5 Tooling & Execution

```bash
pip install pytest httpx pytest-cov

# Run
pytest backend/tests -v --cov=backend/app
```

Add `make test` target for dev + CI.

---

## 6 Incremental Timeline

| Sprint | Focus           | Key Tests                          |
| ------ | --------------- | ---------------------------------- |
| Week 1 | ETL MVP         | Row count, FIPS, geometry non‑null |
| Week 2 | API basics      | /vars, /choropleth happy‑path      |
| Week 3 | Edge‑cases      | invalid var, missing FIPS          |
| Week 4 | Spatial stats   | Moran’s I, correlation sanity      |
| Week 5 | Coverage + perf | 80% of critical paths, <60 s suite |

---

## 7 Success Metrics

* **Green CI** on every PR within < 60 seconds.
* **≥15 targeted tests** covering ETL, API contracts, stats.
* **0 silent data‑integrity bugs** in production after launch.

---

> *“If you can’t write a failing test for it, you don’t understand it.”* — pragmatic mantra
