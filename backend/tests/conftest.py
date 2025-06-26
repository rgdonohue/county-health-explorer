"""
Pytest configuration and fixtures for County Health Explorer tests.
"""

import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.database import DatabaseManager
from backend.app.etl import CountyHealthETL
from backend.app.main import app


@pytest.fixture(scope="session")
def test_db_path():
    """Create a temporary database file for testing."""
    # Create a temporary file that doesn't exist yet - DuckDB will create it
    import tempfile
    fd, tmp_path = tempfile.mkstemp(suffix='.duckdb')
    os.close(fd)  # Close file descriptor
    os.unlink(tmp_path)  # Remove the empty file so DuckDB can create it fresh
    
    yield tmp_path
    
    # Cleanup
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


@pytest.fixture(scope="session") 
def test_db_manager(test_db_path):
    """Create a test database manager instance."""
    db_manager = DatabaseManager(test_db_path)
    yield db_manager
    db_manager.close()


@pytest.fixture(scope="session")
def test_etl(test_db_manager):
    """Create ETL instance with test database."""
    return CountyHealthETL(test_db_manager)


@pytest.fixture(scope="session")
def sample_health_csv(tmp_path_factory):
    """Create a small sample health CSV for testing."""
    tmp_dir = tmp_path_factory.mktemp("test_data")
    csv_path = tmp_dir / "sample_health.csv"
    
    # Create minimal sample data matching the actual CSV structure
    sample_data = '''5-digit FIPS Code,County,State,Premature death raw value,Adult obesity raw value,Adult smoking raw value
01001,Autauga County,Alabama,7890,32.1,17.8
01003,Baldwin County,Alabama,6543,28.9,15.2
01005,Barbour County,Alabama,9876,35.4,21.3
01007,Bibb County,Alabama,8765,33.7,19.1
01009,Blount County,Alabama,7654,31.2,18.4'''
    
    csv_path.write_text(sample_data)
    return str(csv_path)


@pytest.fixture(scope="session")
def sample_spatial_geojson(tmp_path_factory):
    """Create a small sample GeoJSON for testing."""
    tmp_dir = tmp_path_factory.mktemp("test_data")
    geojson_path = tmp_dir / "sample_counties.json"
    
    # Create minimal sample GeoJSON with 5 counties
    sample_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "GEOID": "01001",
                    "NAME": "Autauga County",
                    "STATEFP": "01"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-86.5, 32.5], [-86.4, 32.5], [-86.4, 32.6], [-86.5, 32.6], [-86.5, 32.5]]]
                }
            },
            {
                "type": "Feature", 
                "properties": {
                    "GEOID": "01003",
                    "NAME": "Baldwin County",
                    "STATEFP": "01"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-87.5, 30.5], [-87.4, 30.5], [-87.4, 30.6], [-87.5, 30.6], [-87.5, 30.5]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "GEOID": "01005", 
                    "NAME": "Barbour County",
                    "STATEFP": "01"  
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-85.5, 31.5], [-85.4, 31.5], [-85.4, 31.6], [-85.5, 31.6], [-85.5, 31.5]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "GEOID": "01007",
                    "NAME": "Bibb County", 
                    "STATEFP": "01"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-87.1, 33.0], [-87.0, 33.0], [-87.0, 33.1], [-87.1, 33.1], [-87.1, 33.0]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "GEOID": "01009",
                    "NAME": "Blount County",
                    "STATEFP": "01"
                },
                "geometry": {
                    "type": "Polygon", 
                    "coordinates": [[[-86.9, 33.8], [-86.8, 33.8], [-86.8, 33.9], [-86.9, 33.9], [-86.9, 33.8]]]
                }
            }
        ]
    }
    
    import json
    geojson_path.write_text(json.dumps(sample_geojson))
    return str(geojson_path)


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture(scope="session")
def loaded_test_etl(test_etl, sample_health_csv, sample_spatial_geojson):
    """ETL instance with sample data already loaded."""
    # Load the sample data
    test_etl.load_county_health_data(sample_health_csv)
    test_etl.load_spatial_data(sample_spatial_geojson)
    test_etl.create_joined_view()
    return test_etl 