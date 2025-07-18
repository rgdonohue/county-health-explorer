# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The County Health Explorer is a full-stack spatial data science application for exploring U.S. county-level health indicators. It combines a FastAPI backend with DuckDB spatial database and a vanilla JavaScript frontend using Observable Plot for mapping.

## Architecture

### Backend (FastAPI + DuckDB)
- **Main Application**: `backend/app/main.py` - FastAPI app with CORS and error handling
- **Database**: `backend/app/database.py` - DuckDB with spatial extension manager
- **ETL Pipeline**: `backend/app/etl.py` - Data transformation and loading
- **API Routes**: `backend/app/routes/api.py` - REST endpoints for health data
- **Database File**: `data/county_health.duckdb` - DuckDB database with spatial data

### Frontend (Vanilla JavaScript)
- **Main Entry**: `frontend/index.html` - Single page application
- **JavaScript Modules**: `frontend/js/` - ES6 modules for API, mapping, UI
- **Styling**: `frontend/css/styles.css` - Custom CSS with Inter font
- **Observable Plot**: Uses D3 and Observable Plot for cartographic mapping

### Data Pipeline
- **Health Data**: `data/analytic_data2025_v2.csv` - County health metrics
- **Spatial Data**: `data/counties.json` - County boundary GeoJSON
- **Metadata**: `data/DataDictionary_2025.csv` - Variable definitions

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run ETL pipeline (first time setup)
PYTHONPATH=backend python -m app.etl
```

### Running Servers
```bash
# Start both servers individually (recommended approach):

# Terminal 1 - Backend server
cd backend && ../venv/bin/python3 -m uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend server
python serve_frontend.py

# Alternative: Use the start_dev.py script (may need debugging)
python start_dev.py
```

### Testing
```bash
# Run backend tests
source venv/bin/activate && python -m pytest backend/tests/ -v

# Note: Some tests may fail due to database schema mismatches in test fixtures
```

## Key Implementation Details

### State Management
The frontend uses a central `AppState` object in `frontend/js/main.js`:
```javascript
const AppState = {
    currentVariable: 'premature_death',
    selectedCounty: null,
    mapLoaded: false,
    projection: 'albers-usa'
};
```

### Database Schema
- `county_health`: Health metrics with normalized column names
- `county_spatial`: GeoJSON features with WKB geometries
- `counties_with_geometry`: Joined view for API responses
- `variable_metadata`: Variable definitions and categories

### API Endpoints
- `GET /api/vars` - List all health variables
- `GET /api/choropleth?var=<variable>` - GeoJSON with health data
- `GET /api/stats?var=<variable>` - Summary statistics
- `GET /api/moran?var=<variable>` - Spatial autocorrelation
- `GET /health` - Health check endpoint

### ETL Pipeline Process
1. Load health data CSV with column normalization
2. Load spatial GeoJSON with geometry validation
3. Create joined view with proper FIPS code matching
4. Load variable metadata from data dictionary
5. Validate data integrity and join completeness

## Common Issues and Solutions

### Database Locking
DuckDB uses file-based locking. If you encounter lock errors:
```bash
# Kill any running processes
pkill -f uvicorn
# Remove database file to reset
rm data/county_health.duckdb
# Re-run ETL
PYTHONPATH=backend python -m app.etl
```

### Import Errors
When running ETL or tests, use `PYTHONPATH=backend` to resolve relative imports:
```bash
PYTHONPATH=backend python -m app.etl
```

### Test Failures
Several test failures are expected due to:
- Database schema mismatches in test fixtures
- Column name differences between test and production data
- Missing endpoints not yet implemented

## Code Style and Patterns

### Backend Patterns
- Use context managers for database connections: `with db.get_cursor() as conn:`
- Follow FastAPI dependency injection patterns
- Use proper exception handling with detailed logging
- Return structured JSON responses with consistent error formats

### Frontend Patterns
- ES6 modules with explicit imports/exports
- Observable Plot for all mapping and visualization
- Central state management through AppState object
- Event-driven architecture with proper binding

### Database Patterns
- Use DuckDB spatial extension for geometry operations
- Normalize column names during ETL (remove spaces, lowercase)
- Create views for complex joins rather than in-memory processing
- Use prepared statements for dynamic queries

## Performance Considerations

- DuckDB queries are optimized for analytical workloads
- Frontend uses efficient SVG rendering through Observable Plot
- API responses include proper caching headers
- Spatial operations use indexed geometry columns

## Security Notes

- CORS is configured for development (allow all origins)
- No authentication/authorization implemented
- Input validation on API parameters
- SQL injection prevention through parameterized queries