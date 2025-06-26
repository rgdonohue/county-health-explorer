"""
API routes for County Health Explorer.
Implements all endpoints specified in the PRD.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import numpy as np
from scipy.stats import pearsonr

from ..database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


def get_health_variables() -> List[Dict[str, str]]:
    """Get list of available health variables from the database."""
    try:
        db = get_db()
        with db.get_cursor() as conn:
            # Get all columns from county_health table
            result = conn.execute("DESCRIBE county_health").fetchall()
            
            variables = []
            for row in result:
                col_name = row[0]  # First column is the name
                col_type = row[1]  # Second column is the type
                if "raw value" in col_name:
                    # Extract clean variable name
                    clean_name = col_name.replace(" raw value", "").lower().replace(" ", "_")
                    variables.append({
                        "name": clean_name,
                        "display_name": col_name.replace(" raw value", ""),
                        "column": col_name,
                        "type": "numeric"
                    })
            
            return variables
            
    except Exception as e:
        logger.error(f"Failed to get health variables: {e}", exc_info=True)
        raise Exception(f"Failed to retrieve variables: {str(e)}")


def validate_variable(variable: str) -> str:
    """Validate and return the actual column name for a variable."""
    variables = get_health_variables()
    var_map = {v["name"]: v["column"] for v in variables}
    
    if variable not in var_map:
        available_vars = list(var_map.keys())[:10]  # Show first 10
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid variable name",
                "status": 400,
                "details": f"Variable '{variable}' not found in dataset. Available: {available_vars}..."
            }
        )
    
    return var_map[variable]


@router.get("/debug/columns")
async def debug_columns():
    """Debug endpoint to see all columns."""
    try:
        db = get_db()
        with db.get_cursor() as conn:
            result = conn.execute("DESCRIBE county_health").fetchall()
            columns = [{"name": col[0], "type": col[1]} for col in result]
            raw_value_cols = [col for col in columns if "raw value" in col["name"]]
            return {
                "total_columns": len(columns),
                "raw_value_columns": len(raw_value_cols),
                "first_10_raw_value": raw_value_cols[:10],
                "sample_columns": columns[:10]
            }
    except Exception as e:
        logger.error(f"Debug error: {e}")
        return {"error": str(e)}

@router.get("/vars")
async def get_variables():
    """Get list of available variables and metadata."""
    try:
        db = get_db()
        with db.get_cursor() as conn:
            # Get all columns from county_health table
            result = conn.execute("DESCRIBE county_health").fetchall()
            
            variables = []
            for row in result:
                col_name = row[0]  # First column is the name
                col_type = row[1]  # Second column is the type
                if "raw value" in col_name:
                    # Extract clean variable name
                    clean_name = col_name.replace(" raw value", "").lower().replace(" ", "_")
                    variables.append({
                        "name": clean_name,
                        "display_name": col_name.replace(" raw value", ""),
                        "column": col_name,
                        "type": "numeric"
                    })
        
        return {
            "variables": variables,
            "count": len(variables)
        }
    except Exception as e:
        logger.error(f"Error in get_variables: {e}", exc_info=True)
        return {"error": str(e), "variables": [], "count": 0}


@router.get("/variables/categories")
async def get_variable_categories():
    """Get variables grouped by health domain."""
    try:
        variables = get_health_variables()
        
        # Group variables by category based on common themes
        categories = {
            "mortality": [],
            "behavioral": [],
            "clinical": [],
            "social": [],
            "physical_environment": [],
            "demographics": []
        }
        
        for var in variables:
            name = var["display_name"].lower()
            if any(term in name for term in ["death", "mortality", "life expectancy"]):
                categories["mortality"].append(var)
            elif any(term in name for term in ["smoking", "drinking", "obesity", "physical inactivity"]):
                categories["behavioral"].append(var)
            elif any(term in name for term in ["health days", "diabetes", "hiv", "mental"]):
                categories["clinical"].append(var)
            elif any(term in name for term in ["income", "poverty", "education", "unemployment"]):
                categories["social"].append(var)
            elif any(term in name for term in ["air pollution", "water", "housing"]):
                categories["physical_environment"].append(var)
            else:
                categories["demographics"].append(var)
        
        return categories
        
    except Exception as e:
        logger.error(f"Error in get_variable_categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_variable_stats(var: str = Query(..., description="Variable name")):
    """Get summary statistics for a variable."""
    try:
        column_name = validate_variable(var)
        
        db = get_db()
        with db.get_cursor() as conn:
            # Get statistics, handling potential string values
            result = conn.execute(f"""
                SELECT 
                    COUNT(*) as count,
                    COUNT(CASE WHEN "{column_name}" IS NOT NULL AND "{column_name}" != '' THEN 1 END) as valid_count,
                    AVG(CASE WHEN "{column_name}" ~ '^[0-9.]+$' THEN CAST("{column_name}" AS DOUBLE) END) as mean,
                    STDDEV(CASE WHEN "{column_name}" ~ '^[0-9.]+$' THEN CAST("{column_name}" AS DOUBLE) END) as std,
                    MIN(CASE WHEN "{column_name}" ~ '^[0-9.]+$' THEN CAST("{column_name}" AS DOUBLE) END) as min,
                    MAX(CASE WHEN "{column_name}" ~ '^[0-9.]+$' THEN CAST("{column_name}" AS DOUBLE) END) as max
                FROM counties_with_geometry
                WHERE geometry IS NOT NULL
            """).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="No data found for variable")
            
            return {
                "variable": var,
                "count": result[1],  # valid_count
                "mean": round(result[2], 3) if result[2] is not None else None,
                "std": round(result[3], 3) if result[3] is not None else None,
                "min": result[4],
                "max": result[5]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_variable_stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/choropleth")
async def get_choropleth(var: str = Query(..., description="Variable name")):
    """Return GeoJSON with joined data and class breaks for choropleth mapping."""
    try:
        column_name = validate_variable(var)
        
        db = get_db()
        with db.get_cursor() as conn:
            # Get data with geometries
            result = conn.execute(f"""
                SELECT 
                    "5-digit FIPS Code" as fips,
                    "Name" as county_name,
                    "State Abbreviation" as state,
                    "{column_name}" as value,
                    ST_AsGeoJSON(geometry) as geometry_json
                FROM counties_with_geometry
                WHERE geometry IS NOT NULL 
                  AND "{column_name}" IS NOT NULL 
                  AND "{column_name}" != ''
                  AND "{column_name}" ~ '^[0-9.]+$'
            """).fetchall()
            
            if not result:
                raise HTTPException(status_code=404, detail="No valid data found for variable")
            
            # Extract numeric values for classification
            values = []
            features = []
            
            for row in result:
                try:
                    value = float(row[3])
                    values.append(value)
                    
                    # Parse geometry JSON
                    geometry = json.loads(row[4])
                    
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "fips": row[0],
                            "county_name": row[1],
                            "state": row[2],
                            "value": value
                        },
                        "geometry": geometry
                    })
                except (ValueError, json.JSONDecodeError):
                    continue
            
            if not values:
                raise HTTPException(status_code=404, detail="No valid numeric data found")
            
            # Create class breaks using quantiles
            values_array = np.array(values)
            quantiles = np.quantile(values_array, [0, 0.2, 0.4, 0.6, 0.8, 1.0])
            
            # Assign classes to features
            for feature in features:
                value = feature["properties"]["value"]
                class_num = 1
                for i, threshold in enumerate(quantiles[1:], 1):
                    if value <= threshold:
                        class_num = i
                        break
                feature["properties"]["class"] = class_num
            
            return {
                "type": "FeatureCollection",
                "features": features,
                "metadata": {
                    "variable": var,
                    "count": len(features),
                    "class_breaks": quantiles.tolist()
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_choropleth: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/corr")
async def get_correlation(vars: str = Query(..., description="Comma-separated variable names")):
    """Get correlation between two variables."""
    try:
        var_list = [v.strip() for v in vars.split(",")]
        if len(var_list) != 2:
            raise HTTPException(
                status_code=400,
                detail="Exactly two variables required, separated by comma"
            )
        
        var1, var2 = var_list
        col1 = validate_variable(var1)
        col2 = validate_variable(var2)
        
        db = get_db()
        with db.get_cursor() as conn:
            # Get paired data
            result = conn.execute(f"""
                SELECT 
                    "{col1}" as var1_value,
                    "{col2}" as var2_value
                FROM counties_with_geometry
                WHERE geometry IS NOT NULL 
                  AND "{col1}" IS NOT NULL AND "{col1}" != '' AND "{col1}" ~ '^[0-9.]+$'
                  AND "{col2}" IS NOT NULL AND "{col2}" != '' AND "{col2}" ~ '^[0-9.]+$'
            """).fetchall()
            
            if len(result) < 10:  # Need minimum data points
                raise HTTPException(status_code=400, detail="Insufficient valid data for correlation")
            
            # Extract values and calculate correlation
            values1 = [float(row[0]) for row in result]
            values2 = [float(row[1]) for row in result]
            
            correlation, p_value = pearsonr(values1, values2)
            
            return {
                "var1": var1,
                "var2": var2,
                "correlation": round(correlation, 3),
                "p_value": round(p_value, 6),
                "n": len(values1)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_correlation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/counties/{fips}")
async def get_county_details(fips: str):
    """Get individual county details."""
    try:
        if len(fips) != 5 or not fips.isdigit():
            raise HTTPException(
                status_code=400,
                detail="FIPS code must be exactly 5 digits"
            )
        
        db = get_db()
        with db.get_cursor() as conn:
            # Get county details
            result = conn.execute(f"""
                SELECT 
                    "5-digit FIPS Code" as fips,
                    "Name" as county_name,
                    "State Abbreviation" as state,
                    "Premature Death raw value" as premature_death,
                    "Adult Obesity raw value" as obesity,
                    "Adult Smoking raw value" as smoking,
                    "Physical Inactivity raw value" as physical_inactivity,
                    "Median Household Income raw value" as median_income,
                    ST_AsGeoJSON(geometry) as geometry_json
                FROM counties_with_geometry
                WHERE "5-digit FIPS Code" = '{fips}'
            """).fetchone()
            
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "County not found",
                        "status": 404,
                        "details": f"FIPS code '{fips}' not found in dataset"
                    }
                )
            
            # Parse geometry if available
            geometry = None
            if result[8]:
                try:
                    geometry = json.loads(result[8])
                except json.JSONDecodeError:
                    pass
            
            return {
                "fips": result[0],
                "county_name": result[1],
                "state": result[2],
                "health_indicators": {
                    "premature_death": result[3],
                    "obesity": result[4],
                    "smoking": result[5],
                    "physical_inactivity": result[6],
                    "median_income": result[7]
                },
                "geometry": geometry
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_county_details: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/neighbors/{fips}")
async def get_county_neighbors(fips: str):
    """Get spatial neighbors for local analysis."""
    try:
        if len(fips) != 5 or not fips.isdigit():
            raise HTTPException(
                status_code=400,
                detail="FIPS code must be exactly 5 digits"
            )
        
        db = get_db()
        with db.get_cursor() as conn:
            # Find neighboring counties using spatial touches
            result = conn.execute(f"""
                WITH target_county AS (
                    SELECT geometry, "Name" as target_name
                    FROM counties_with_geometry 
                    WHERE "5-digit FIPS Code" = '{fips}'
                )
                SELECT 
                    c."5-digit FIPS Code" as fips,
                    c."Name" as county_name,
                    c."State Abbreviation" as state
                FROM counties_with_geometry c, target_county t
                WHERE c."5-digit FIPS Code" != '{fips}'
                  AND ST_Touches(c.geometry, t.geometry)
                ORDER BY c."Name"
            """).fetchall()
            
            neighbors = []
            for row in result:
                neighbors.append({
                    "fips": row[0],
                    "county_name": row[1],
                    "state": row[2]
                })
            
            return {
                "target_fips": fips,
                "neighbors": neighbors,
                "count": len(neighbors)
            }
            
    except Exception as e:
        logger.error(f"Error in get_county_neighbors: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/moran")
async def get_moran_i(var: str = Query(..., description="Variable name")):
    """Calculate Moran's I spatial autocorrelation statistic."""
    try:
        column_name = validate_variable(var)
        
        # Import PySAL for spatial statistics
        try:
            from libpysal import weights
            from esda import Moran
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="Spatial statistics not available - PySAL not properly installed"
            )
        
        db = get_db()
        with db.get_cursor() as conn:
            # Get county data with centroids for spatial weights
            result = conn.execute(f"""
                SELECT 
                    "5-digit FIPS Code" as fips,
                    CASE WHEN "{column_name}" ~ '^[0-9.]+$' 
                         THEN CAST("{column_name}" AS DOUBLE) 
                         ELSE NULL END as value,
                    ST_X(ST_Centroid(geometry)) as lon,
                    ST_Y(ST_Centroid(geometry)) as lat
                FROM counties_with_geometry
                WHERE geometry IS NOT NULL 
                  AND "{column_name}" IS NOT NULL 
                  AND "{column_name}" != ''
                  AND "{column_name}" ~ '^[0-9.]+$'
                ORDER BY "5-digit FIPS Code"
            """).fetchall()
            
            if len(result) < 50:  # Need sufficient data for spatial analysis
                raise HTTPException(
                    status_code=400,
                    detail="Insufficient data for spatial autocorrelation analysis"
                )
            
            # Extract coordinates and values
            coords = [(row[2], row[3]) for row in result if row[1] is not None]
            values = [row[1] for row in result if row[1] is not None]
            
            if len(values) < 50:
                raise HTTPException(
                    status_code=400,
                    detail="Insufficient valid numeric data for analysis"
                )
            
            # Create spatial weights matrix (KNN with k=8)
            w = weights.KNN.from_array(coords, k=8)
            w.transform = 'r'  # Row standardization
            
            # Calculate Moran's I
            moran = Moran(values, w)
            
            return {
                "variable": var,
                "moran_i": round(moran.I, 4),
                "expected_i": round(moran.EI, 4),
                "variance": round(moran.VI_norm, 6),
                "z_score": round(moran.z_norm, 4),
                "p_value": round(moran.p_norm, 6),
                "n": len(values),
                "interpretation": "positive" if moran.I > moran.EI else "negative" if moran.I < moran.EI else "random"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_moran_i: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 