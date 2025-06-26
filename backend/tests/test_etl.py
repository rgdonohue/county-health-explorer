"""
ETL Pipeline Tests for County Health Explorer.

Tests data pipeline integrity as specified in testing-strategy.md:
- County count validation
- FIPS uniqueness 
- Geometry validation
- Data type validation
- Spatial join integrity
"""

import pytest


class TestETLDataLoading:
    """Test ETL data loading operations."""
    
    def test_health_data_loading(self, test_etl, sample_health_csv):
        """Test loading county health data from CSV."""
        # Load data
        row_count = test_etl.load_county_health_data(sample_health_csv)
        
        # Verify row count
        assert row_count == 5, f"Expected 5 rows, got {row_count}"
        
        # Verify data exists in database
        with test_etl.db.get_cursor() as conn:
            result = conn.execute("SELECT COUNT(*) FROM county_health").fetchone()
            assert result[0] == 5
    
    def test_spatial_data_loading(self, test_etl, sample_spatial_geojson):
        """Test loading spatial data from GeoJSON."""
        # Load spatial data
        row_count = test_etl.load_spatial_data(sample_spatial_geojson)
        
        # Verify row count
        assert row_count == 5, f"Expected 5 spatial records, got {row_count}"
        
        # Verify spatial data exists
        with test_etl.db.get_cursor() as conn:
            result = conn.execute("SELECT COUNT(*) FROM county_spatial").fetchone()
            assert result[0] == 5
    
    def test_joined_view_creation(self, loaded_test_etl):
        """Test creation of joined view with health and spatial data."""
        etl = loaded_test_etl
        
        # Verify joined view exists and has correct count
        with etl.db.get_cursor() as conn:
            result = conn.execute("SELECT COUNT(*) FROM counties_with_geometry").fetchone()
            assert result[0] == 5, "Joined view should have 5 records"
            
            # Verify geometry is present
            result = conn.execute("""
                SELECT COUNT(*) FROM counties_with_geometry 
                WHERE geometry IS NOT NULL
            """).fetchone()
            assert result[0] == 5, "All records should have geometry"


class TestETLDataIntegrity:
    """Test ETL data integrity requirements."""
    
    def test_fips_uniqueness(self, loaded_test_etl):
        """Test that FIPS codes are unique in health data."""
        etl = loaded_test_etl
        
        with etl.db.get_cursor() as conn:
            # Check for duplicate FIPS codes
            result = conn.execute("""
                SELECT COUNT(*) - COUNT(DISTINCT "5-digit FIPS Code") as duplicates
                FROM county_health
            """).fetchone()
            
            duplicates = result[0] if result else 0
            assert duplicates == 0, f"Found {duplicates} duplicate FIPS codes"
    
    def test_fips_format_validation(self, loaded_test_etl):
        """Test that FIPS codes are properly formatted 5-digit strings."""
        etl = loaded_test_etl
        
        with etl.db.get_cursor() as conn:
            # Check FIPS format (should be 5 characters)
            result = conn.execute("""
                SELECT COUNT(*) FROM county_health 
                WHERE LENGTH("5-digit FIPS Code") != 5
            """).fetchone()
            
            invalid_fips = result[0] if result else 0
            assert invalid_fips == 0, f"Found {invalid_fips} invalid FIPS codes"
    
    def test_geometry_validity(self, loaded_test_etl):
        """Test that all geometries are valid and non-null."""
        etl = loaded_test_etl
        
        with etl.db.get_cursor() as conn:
            # Check for null geometries after join
            result = conn.execute("""
                SELECT COUNT(*) FROM counties_with_geometry 
                WHERE geometry IS NULL
            """).fetchone()
            
            null_geometries = result[0] if result else 0
            assert null_geometries == 0, f"Found {null_geometries} null geometries"
            
            # Check geometry validity using spatial functions
            result = conn.execute("""
                SELECT COUNT(*) FROM counties_with_geometry 
                WHERE NOT ST_IsValid(geometry)
            """).fetchone()
            
            invalid_geometries = result[0] if result else 0
            assert invalid_geometries == 0, f"Found {invalid_geometries} invalid geometries"
    
    def test_spatial_join_completeness(self, loaded_test_etl):
        """Test that spatial join is complete - all health records have geometry."""
        etl = loaded_test_etl
        
        validation_results = etl.validate_data()
        
        # Check join success rate
        assert validation_results['join_success_rate'] == 100.0, \
            f"Join success rate is {validation_results['join_success_rate']}%, expected 100%"
        
        # Check for missing geometries
        assert validation_results['missing_geometries'] == 0, \
            f"Found {validation_results['missing_geometries']} missing geometries"


class TestETLDataValidation:
    """Test ETL data validation functions."""
    
    def test_validation_results_structure(self, loaded_test_etl):
        """Test that validation returns proper result structure."""
        etl = loaded_test_etl
        
        results = etl.validate_data()
        
        # Check required keys are present
        required_keys = [
            'health_records', 'spatial_records', 'joined_records',
            'missing_geometries', 'duplicate_fips', 'join_success_rate'
        ]
        
        for key in required_keys:
            assert key in results, f"Missing key '{key}' in validation results"
        
        # Check data types
        assert isinstance(results['health_records'], int)
        assert isinstance(results['spatial_records'], int)
        assert isinstance(results['joined_records'], int)
        assert isinstance(results['missing_geometries'], int)
        assert isinstance(results['duplicate_fips'], int)
        assert isinstance(results['join_success_rate'], (int, float))
    
    def test_health_variable_ranges(self, loaded_test_etl):
        """Test that health variables are within reasonable ranges."""
        etl = loaded_test_etl
        
        with etl.db.get_cursor() as conn:
            # Test premature death values (should be positive)
            result = conn.execute("""
                SELECT MIN(CAST("Premature death raw value" AS DOUBLE)) as min_val,
                       MAX(CAST("Premature death raw value" AS DOUBLE)) as max_val
                FROM county_health
                WHERE regexp_full_match(CAST("Premature death raw value" AS VARCHAR), '^[0-9.]+$')
            """).fetchone()
            
            if result and result[0] is not None:
                min_val, max_val = result
                assert min_val > 0, f"Premature death minimum value {min_val} should be positive"
                assert max_val < 50000, f"Premature death maximum value {max_val} seems too high"
            
            # Test obesity percentages (should be 0-100)
            result = conn.execute("""
                SELECT MIN(CAST("Adult obesity raw value" AS DOUBLE)) as min_val,
                       MAX(CAST("Adult obesity raw value" AS DOUBLE)) as max_val  
                FROM county_health
                WHERE regexp_full_match(CAST("Adult obesity raw value" AS VARCHAR), '^[0-9.]+$')
            """).fetchone()
            
            if result and result[0] is not None:
                min_val, max_val = result
                assert 0 <= min_val <= 100, f"Obesity percentage {min_val} should be 0-100"
                assert 0 <= max_val <= 100, f"Obesity percentage {max_val} should be 0-100"


class TestETLFullPipeline:
    """Test complete ETL pipeline execution."""
    
    def test_full_etl_execution(self, test_etl, sample_health_csv, sample_spatial_geojson):
        """Test complete ETL pipeline from start to finish."""
        etl = test_etl
        
        # Run full ETL pipeline
        results = etl.run_full_etl(sample_health_csv, sample_spatial_geojson)
        
        # Check success
        assert results['success'] is True, f"ETL failed: {results.get('error', 'Unknown error')}"
        
        # Check row counts
        assert results['health_rows_loaded'] == 5
        assert results['spatial_rows_loaded'] == 5
        
        # Check validation results
        validation = results['validation']
        assert validation['health_records'] == 5
        assert validation['spatial_records'] == 5
        assert validation['joined_records'] == 5
        assert validation['missing_geometries'] == 0
        assert validation['duplicate_fips'] == 0
        assert validation['join_success_rate'] == 100.0


# Performance and error handling tests
class TestETLPerformance:
    """Test ETL performance and error handling."""
    
    def test_invalid_csv_path(self, test_etl):
        """Test handling of invalid CSV path."""
        with pytest.raises(Exception):
            test_etl.load_county_health_data("nonexistent_file.csv")
    
    def test_invalid_geojson_path(self, test_etl):
        """Test handling of invalid GeoJSON path.""" 
        with pytest.raises(Exception):
            test_etl.load_spatial_data("nonexistent_file.json")
    
    def test_spatial_functionality(self, test_etl):
        """Test that spatial functionality is working in test database."""
        assert test_etl.db.test_spatial_functionality() is True, \
            "Spatial functionality should work in test database" 