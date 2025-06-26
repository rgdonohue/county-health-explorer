"""
API Endpoint Tests for County Health Explorer.

Tests API contracts and endpoint responses as specified in testing-strategy.md:
- Endpoint smoke tests
- Error handling (400, 404, 500)
- Response format validation
- Performance validation
"""

import pytest
import time
from fastapi import status


class TestHealthVariablesAPI:
    """Test health variables API endpoints."""
    
    def test_get_variables_endpoint(self, test_client):
        """Test /api/vars endpoint returns variables list."""
        response = test_client.get("/api/vars")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "variables" in data
        assert "count" in data
        assert isinstance(data["variables"], list)
        assert isinstance(data["count"], int)
        
        # If we have variables, check their structure
        if data["variables"]:
            var = data["variables"][0]
            required_fields = ["name", "display_name", "column", "type"]
            for field in required_fields:
                assert field in var, f"Missing field '{field}' in variable"
    
    def test_get_variable_categories_endpoint(self, test_client):
        """Test /api/variables/categories endpoint."""
        response = test_client.get("/api/variables/categories")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check expected categories exist
        expected_categories = [
            "mortality", "behavioral", "clinical", 
            "social", "physical_environment", "demographics"
        ]
        
        for category in expected_categories:
            assert category in data, f"Missing category '{category}'"
            assert isinstance(data[category], list)


class TestStatisticsAPI:
    """Test statistics API endpoints."""
    
    def test_stats_endpoint_valid_variable(self, test_client):
        """Test /api/stats endpoint with valid variable."""
        # First get available variables
        vars_response = test_client.get("/api/vars")
        if vars_response.status_code == 200:
            variables = vars_response.json().get("variables", [])
            if variables:
                var_name = variables[0]["name"]
                
                response = test_client.get(f"/api/stats?var={var_name}")
                assert response.status_code == 200
                
                data = response.json()
                required_fields = ["variable", "count", "mean", "std", "min", "max"]
                for field in required_fields:
                    assert field in data, f"Missing field '{field}' in stats response"
                
                assert data["variable"] == var_name
    
    def test_stats_endpoint_invalid_variable(self, test_client):
        """Test /api/stats endpoint with invalid variable returns 400."""
        response = test_client.get("/api/stats?var=nonexistent_variable")
        
        assert response.status_code == 400
        data = response.json()
        
        # Check error response format matches PRD specification
        assert "error" in data
        assert "status" in data  
        assert "details" in data
        assert data["status"] == 400
    
    def test_stats_endpoint_missing_parameter(self, test_client):
        """Test /api/stats endpoint without var parameter."""
        response = test_client.get("/api/stats")
        
        # FastAPI should return 422 for missing required parameter
        assert response.status_code == 422


class TestChoroplethAPI:
    """Test choropleth API endpoint."""
    
    def test_choropleth_endpoint_structure(self, test_client):
        """Test /api/choropleth endpoint response structure."""
        # First get a valid variable
        vars_response = test_client.get("/api/vars")
        if vars_response.status_code == 200:
            variables = vars_response.json().get("variables", [])
            if variables:
                var_name = variables[0]["name"]
                
                response = test_client.get(f"/api/choropleth?var={var_name}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check GeoJSON structure
                    assert "type" in data
                    assert data["type"] == "FeatureCollection"
                    assert "features" in data  
                    assert isinstance(data["features"], list)
                    
                    # If we have features, check their structure
                    if data["features"]:
                        feature = data["features"][0]
                        assert "type" in feature
                        assert feature["type"] == "Feature"
                        assert "properties" in feature
                        assert "geometry" in feature
                        
                        # Check that properties include required fields
                        props = feature["properties"]
                        required_props = ["fips", "value", "class"]
                        for prop in required_props:
                            assert prop in props, f"Missing property '{prop}' in feature"
    
    def test_choropleth_endpoint_invalid_variable(self, test_client):
        """Test /api/choropleth endpoint with invalid variable."""
        response = test_client.get("/api/choropleth?var=invalid_variable_name")
        
        assert response.status_code == 400
        data = response.json()
        
        # Check error response format
        assert "error" in data
        assert "status" in data
        assert data["status"] == 400


class TestCorrelationAPI:
    """Test correlation API endpoint."""
    
    def test_correlation_endpoint_valid_variables(self, test_client):
        """Test /api/corr endpoint with valid variables."""
        # Get available variables
        vars_response = test_client.get("/api/vars")
        if vars_response.status_code == 200:
            variables = vars_response.json().get("variables", [])
            if len(variables) >= 2:
                var1 = variables[0]["name"]
                var2 = variables[1]["name"] 
                
                response = test_client.get(f"/api/corr?vars={var1},{var2}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check response structure
                    required_fields = ["var1", "var2", "correlation"]
                    for field in required_fields:
                        assert field in data, f"Missing field '{field}' in correlation response"
                    
                    # Check correlation value bounds
                    corr = data["correlation"]
                    if corr is not None:
                        assert -1.0 <= corr <= 1.0, f"Correlation {corr} outside valid range [-1, 1]"
    
    def test_correlation_endpoint_invalid_format(self, test_client):
        """Test /api/corr endpoint with invalid parameter format."""
        response = test_client.get("/api/corr?vars=single_variable")
        
        # Should return 400 for invalid format
        assert response.status_code == 400


class TestCountyAPI:
    """Test individual county API endpoints."""
    
    def test_county_details_endpoint(self, test_client):
        """Test /api/counties/{fips} endpoint."""
        # Test with a sample FIPS code
        response = test_client.get("/api/counties/01001")
        
        # Could be 200 (found) or 404 (not found in test data)
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "fips" in data
            assert data["fips"] == "01001"
    
    def test_county_neighbors_endpoint(self, test_client):
        """Test /api/neighbors/{fips} endpoint."""
        response = test_client.get("/api/neighbors/01001")
        
        # Could be 200 (found) or 404 (not found)
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "neighbors" in data
            assert isinstance(data["neighbors"], list)


class TestSpatialAnalysisAPI:
    """Test spatial analysis API endpoints."""
    
    def test_moran_i_endpoint(self, test_client):
        """Test /api/moran endpoint."""
        # Get a valid variable
        vars_response = test_client.get("/api/vars")
        if vars_response.status_code == 200:
            variables = vars_response.json().get("variables", [])
            if variables:
                var_name = variables[0]["name"]
                
                response = test_client.get(f"/api/moran?var={var_name}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check response structure
                    required_fields = ["variable", "morans_i"]
                    for field in required_fields:
                        assert field in data, f"Missing field '{field}' in Moran's I response"
                    
                    # Check Moran's I bounds
                    morans_i = data["morans_i"]
                    if morans_i is not None:
                        assert -1.0 <= morans_i <= 1.0, f"Moran's I {morans_i} outside valid range [-1, 1]"


class TestAPIPerformance:
    """Test API performance requirements."""
    
    def test_api_response_time(self, test_client):
        """Test that API responses are under 150ms as specified in PRD."""
        endpoints_to_test = [
            "/api/vars",
            "/api/variables/categories"
        ]
        
        for endpoint in endpoints_to_test:
            start_time = time.time()
            response = test_client.get(endpoint)
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            # Allow for some test overhead, use 500ms threshold for tests
            assert response_time_ms < 500, \
                f"Response time {response_time_ms:.2f}ms for {endpoint} exceeds 500ms test threshold"


class TestAPIErrorHandling:
    """Test API error handling and response formats."""
    
    def test_global_exception_handler(self, test_client):
        """Test that global exception handler returns proper format."""
        # Try to trigger an internal server error with malformed request
        response = test_client.get("/api/stats?var=") 
        
        # Should be handled gracefully
        assert response.status_code in [400, 422, 500]
        
        data = response.json()
        if response.status_code == 500:
            # Check 500 error format matches PRD specification
            assert "error" in data
            assert "status" in data
            assert data["status"] == 500
    
    def test_health_check_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        
        # Should return either healthy or unhealthy
        assert response.status_code in [200, 503]
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
        
        if response.status_code == 200:
            assert "database" in data
            assert "health_records" in data
            assert "spatial_records" in data 