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
    """Get list of available health variables from the database with metadata."""
    try:
        db = get_db()
        with db.get_cursor() as conn:
            # Get all columns from county_health table
            result = conn.execute("DESCRIBE county_health").fetchall()
            
            # Get metadata if available
            metadata_result = conn.execute("""
                SELECT variable_code, display_name, description, units, data_type, raw_variable
                FROM variable_metadata
            """).fetchall()
            
            # Create metadata lookup by raw variable name
            metadata_lookup = {}
            for meta_row in metadata_result:
                var_code, display_name, description, units, data_type, raw_variable = meta_row
                # Index by the raw variable name for exact matching
                metadata_lookup[raw_variable] = {
                    "variable_code": var_code,
                    "display_name": display_name,
                    "description": description,
                    "units": units,
                    "data_type": data_type,
                    "raw_variable": raw_variable
                }
            
            # Debug: print some metadata for troubleshooting
            logger.info(f"Loaded {len(metadata_lookup)} metadata entries")
            firearm_keys = [k for k in metadata_lookup.keys() if 'firearm' in k.lower()]
            if firearm_keys:
                logger.info(f"Found firearm metadata keys: {firearm_keys}")
            else:
                logger.warning("No firearm metadata found")
            
            variables = []
            for row in result:
                col_name = row[0]  # First column is the name
                col_type = row[1]  # Second column is the type
                
                if "raw value" in col_name:
                    # Extract clean variable name
                    clean_name = col_name.replace(" raw value", "").lower().replace(" ", "_")
                    
                    # Look up metadata by exact column name match
                    var_meta = metadata_lookup.get(col_name)
                    
                    # Debug specific variables
                    if 'firearm' in clean_name.lower():
                        logger.info(f"Processing firearm variable: {col_name}, metadata found: {var_meta is not None}")
                        if var_meta:
                            logger.info(f"Firearm metadata: {var_meta}")
                    
                    variable_info = {
                        "name": clean_name,
                        "display_name": var_meta["display_name"] if var_meta else col_name.replace(" raw value", ""),
                        "column": col_name,
                        "type": "numeric",
                        "description": var_meta["description"] if var_meta else "",
                        "units": var_meta["units"] if var_meta else "",
                        "data_type": var_meta["data_type"] if var_meta else "numeric"
                    }
                    
                    variables.append(variable_info)
            
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
        variables = get_health_variables()
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
            description = var.get("description", "").lower()
            
            if any(term in name for term in ["death", "mortality", "life expectancy", "fatalities", "suicide"]):
                categories["mortality"].append(var)
            elif any(term in name for term in ["smoking", "drinking", "obesity", "physical inactivity"]):
                categories["behavioral"].append(var)
            elif any(term in name for term in ["health days", "diabetes", "hiv", "mental", "distress"]):
                categories["clinical"].append(var)
            elif any(term in name for term in ["income", "poverty", "education", "unemployment", "housing", "associations"]):
                categories["social"].append(var)
            elif any(term in name for term in ["air pollution", "water", "housing", "climate", "environment"]):
                categories["physical_environment"].append(var)
            else:
                categories["demographics"].append(var)
        
        return categories
        
    except Exception as e:
        logger.error(f"Error in get_variable_categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_variable_stats(var: str = Query(..., description="Variable name")):
    """Get summary statistics for a health variable."""
    try:
        # Validate variable and get column name
        column_name = validate_variable(var)
        
        # Get variable metadata for context
        variables = get_health_variables()
        variable_info = next((v for v in variables if v["name"] == var), None)
        
        db = get_db()
        with db.get_cursor() as conn:
            # Get statistics with proper casting for numeric operations
            result = conn.execute(f"""
                SELECT 
                    COUNT(CASE WHEN "{column_name}" IS NOT NULL AND "{column_name}" != '' 
                              AND "{column_name}" ~ '^[0-9.]+$' THEN 1 END) as count,
                    AVG(CASE WHEN "{column_name}" ~ '^[0-9.]+$' 
                             THEN CAST("{column_name}" AS DOUBLE) END) as mean,
                    STDDEV(CASE WHEN "{column_name}" ~ '^[0-9.]+$' 
                                THEN CAST("{column_name}" AS DOUBLE) END) as std,
                    MIN(CASE WHEN "{column_name}" ~ '^[0-9.]+$' 
                             THEN CAST("{column_name}" AS DOUBLE) END) as min,
                    MAX(CASE WHEN "{column_name}" ~ '^[0-9.]+$' 
                             THEN CAST("{column_name}" AS DOUBLE) END) as max,
                    MEDIAN(CASE WHEN "{column_name}" ~ '^[0-9.]+$' 
                                THEN CAST("{column_name}" AS DOUBLE) END) as median
                FROM county_health
                WHERE "{column_name}" IS NOT NULL
            """).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="No data found for variable")
            
            # Smart unit and description detection
            smart_units = ""
            smart_description = ""
            if var == 'premature_death':
                smart_units = "years lost per 100,000"
                smart_description = "Years of potential life lost before age 75 per 100,000 population (age-adjusted)"
            elif var == 'hiv_prevalence':
                smart_units = "per 100,000 population"
                smart_description = "Number of people aged 13 years and older living with a diagnosis of HIV per 100,000 population"
            elif 'health_days' in var:
                smart_units = "days per month"
                smart_description = "Average number of unhealthy days reported in past 30 days (age-adjusted)"
            elif var == 'traffic_volume':
                smart_units = "vehicles per meter per day"
                smart_description = "Average daily traffic volume per meter of road length"
            elif var in ['firearm_fatalities', 'drug_overdose_deaths'] or ('death' in var and 'premature' not in var) or 'mortality' in var:
                smart_units = "per 100,000 population"
                smart_description = "Population-standardized rate for fair comparison"
            elif 'climate' in var or 'adverse_climate' in var:
                smart_units = "0-3 categories"
                smart_description = "Climate threshold categories met (heat, drought, disasters)"
            elif 'obesity' in var or 'smoking' in var or 'physical_inactivity' in var:
                smart_units = "percentage"
                smart_description = "Percentage of adult population"
            elif 'income' in var or 'poverty' in var:
                smart_units = "dollars" if 'income' in var else "percentage"
                smart_description = "Economic indicator"
            elif 'education' in var:
                smart_units = "percentage"
                smart_description = "Educational attainment indicator"
            
            # Format the response with metadata
            response = {
                "variable": var,
                "display_name": variable_info["display_name"] if variable_info else var.replace("_", " ").title(),
                "description": variable_info["description"] if (variable_info and variable_info["description"]) else smart_description,
                "units": variable_info["units"] if (variable_info and variable_info["units"]) else smart_units,
                "data_type": variable_info["data_type"] if variable_info else "numeric",
                "count": int(result[0]) if result[0] else 0,
                "mean": round(float(result[1]), 2) if result[1] else None,
                "std": round(float(result[2]), 2) if result[2] else None,
                "min": round(float(result[3]), 2) if result[3] else None,
                "max": round(float(result[4]), 2) if result[4] else None,
                "median": round(float(result[5]), 2) if result[5] else None
            }
            
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats for {var}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/stats/transformed")
async def get_transformed_variable_stats(var: str = Query(..., description="Variable name")):
    """Get summary statistics for a health variable with proper transformations applied."""
    try:
        # Validate variable and get column name
        column_name = validate_variable(var)
        
        # Get variable metadata for context
        variables = get_health_variables()
        variable_info = next((v for v in variables if v["name"] == var), None)
        
        db = get_db()
        with db.get_cursor() as conn:
            # Get statistics with proper casting for numeric operations
            result = conn.execute(f"""
                SELECT 
                    COUNT(CASE WHEN "{column_name}" IS NOT NULL AND "{column_name}" != '' 
                              AND "{column_name}" ~ '^[0-9.]+$' THEN 1 END) as count,
                    AVG(CASE WHEN "{column_name}" ~ '^[0-9.]+$' 
                             THEN CAST("{column_name}" AS DOUBLE) END) as mean,
                    STDDEV(CASE WHEN "{column_name}" ~ '^[0-9.]+$' 
                                THEN CAST("{column_name}" AS DOUBLE) END) as std,
                    MIN(CASE WHEN "{column_name}" ~ '^[0-9.]+$' 
                             THEN CAST("{column_name}" AS DOUBLE) END) as min,
                    MAX(CASE WHEN "{column_name}" ~ '^[0-9.]+$' 
                             THEN CAST("{column_name}" AS DOUBLE) END) as max,
                    MEDIAN(CASE WHEN "{column_name}" ~ '^[0-9.]+$' 
                                THEN CAST("{column_name}" AS DOUBLE) END) as median
                FROM county_health
                WHERE "{column_name}" IS NOT NULL
            """).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="No data found for variable")
            
            # Define transformation logic (matching frontend metadata.js)
            def transform_value(value, var_name):
                # Variables that need decimal to percentage conversion
                percentage_vars = [
                    'unemployment', 'adult_obesity', 'adult_smoking', 'physical_inactivity',
                    'mammography_screening', 'flu_vaccinations', 'children_in_poverty'
                ]
                
                if value is None:
                    return None
                    
                if var_name in percentage_vars:
                    return float(value) * 100  # Convert decimal to percentage
                
                return float(value)
            
            # Smart unit and description detection with transformation awareness
            smart_units = ""
            smart_description = ""
            
            # Check if this variable needs percentage transformation
            percentage_vars = [
                'unemployment', 'adult_obesity', 'adult_smoking', 'physical_inactivity',
                'mammography_screening', 'flu_vaccinations', 'children_in_poverty'
            ]
            
            if var == 'premature_death':
                smart_units = "years lost per 100,000"
                smart_description = "Years of potential life lost before age 75 per 100,000 population (age-adjusted)"
            elif var == 'hiv_prevalence':
                smart_units = "per 100,000 population"
                smart_description = "Number of people aged 13 years and older living with a diagnosis of HIV per 100,000 population"
            elif var in percentage_vars:
                smart_units = "percentage"
                if var == 'unemployment':
                    smart_description = "Percentage of population ages 16 and older unemployed but seeking work"
                elif var == 'mammography_screening':
                    smart_description = "Percentage of female Medicare enrollees ages 65-74 who received an annual mammography screening"
                elif var == 'adult_obesity':
                    smart_description = "Percentage of adults aged 20 and older with obesity (BMI ≥ 30)"
                else:
                    smart_description = "Percentage value (transformed from decimal)"
            elif 'health_days' in var:
                smart_units = "days per month"
                smart_description = "Average number of unhealthy days reported in past 30 days (age-adjusted)"
            elif var == 'traffic_volume':
                smart_units = "vehicles per meter per day"
                smart_description = "Average daily traffic volume per meter of road length"
            elif var in ['firearm_fatalities', 'drug_overdose_deaths'] or ('death' in var and 'premature' not in var) or 'mortality' in var:
                smart_units = "per 100,000 population"
                smart_description = "Population-standardized rate for fair comparison"
            elif 'climate' in var or 'adverse_climate' in var:
                smart_units = "0-3 categories"
                smart_description = "Climate threshold categories met (heat, drought, disasters)"
            
            # Apply transformations to statistics
            transformed_stats = {
                "count": int(result[0]) if result[0] else 0,
                "mean": transform_value(result[1], var),
                "std": transform_value(result[2], var),
                "min": transform_value(result[3], var),
                "max": transform_value(result[4], var),
                "median": transform_value(result[5], var)
            }
            
            # Format the response with metadata
            response = {
                "variable": var,
                "display_name": variable_info["display_name"] if variable_info else var.replace("_", " ").title(),
                "description": variable_info["description"] if (variable_info and variable_info["description"]) else smart_description,
                "units": variable_info["units"] if (variable_info and variable_info["units"]) else smart_units,
                "data_type": variable_info["data_type"] if variable_info else "numeric",
                "transformed": var in percentage_vars,
                **transformed_stats
            }
            
            # Round values for display
            for key in ['mean', 'std', 'min', 'max', 'median']:
                if response[key] is not None:
                    response[key] = round(response[key], 2)
            
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transformed stats for {var}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/choropleth")
async def get_choropleth(var: str = Query(..., description="Variable name")):
    """Get choropleth data for a health variable."""
    try:
        # Validate variable and get column name
        column_name = validate_variable(var)
        
        # Get variable metadata
        variables = get_health_variables()
        variable_info = next((v for v in variables if v["name"] == var), None)
        
        db = get_db()
        with db.get_cursor() as conn:
            # Use direct table join since view may not exist
            result = conn.execute(f"""
                SELECT 
                    h."5-digit FIPS Code" as fips_code,
                    h."Name" as county_name,
                    h."State Abbreviation" as state_name,
                    CASE WHEN h."{column_name}" ~ '^[0-9.]+$' 
                         THEN CAST(h."{column_name}" AS DOUBLE) END as value,
                    ST_AsGeoJSON(s.geometry) as geometry_json
                FROM county_health h
                INNER JOIN county_spatial s ON h."5-digit FIPS Code" = s.fips_code
                WHERE s.geometry IS NOT NULL
                  AND h."{column_name}" IS NOT NULL
                  AND h."{column_name}" != ''
                  AND h."{column_name}" ~ '^[0-9.]+$'
                ORDER BY h."5-digit FIPS Code"
            """).fetchall()
            
            if not result:
                raise HTTPException(status_code=404, detail="No valid data found for choropleth")
            
            # Calculate quantile breaks for classification
            values = [row[3] for row in result if row[3] is not None]
            
            if not values:
                raise HTTPException(status_code=404, detail="No valid numeric data for choropleth")
            
            # Sort values for quantile calculation
            sorted_values = sorted(values)
            n = len(sorted_values)
            
            if n < 5:
                # Not enough data for proper quantiles
                breaks = [min(values), max(values)]
            else:
                # Calculate quantile breaks (quintiles)
                breaks = [
                    sorted_values[0],  # min
                    sorted_values[max(0, int(n * 0.2) - 1)],  # 20th percentile
                    sorted_values[max(0, int(n * 0.4) - 1)],  # 40th percentile
                    sorted_values[max(0, int(n * 0.6) - 1)],  # 60th percentile
                    sorted_values[max(0, int(n * 0.8) - 1)],  # 80th percentile
                    sorted_values[-1]   # max
                ]
                # Remove duplicates and sort
                breaks = sorted(list(set(breaks)))
            
            # Assign classes based on breaks
            def get_class(value):
                if value is None:
                    return None
                for i in range(len(breaks) - 1):
                    if value <= breaks[i + 1]:
                        return i + 1
                return len(breaks) - 1
            
            # Build GeoJSON
            features = []
            for row in result:
                fips_code, county_name, state_name, value, geometry_json = row
                
                # Parse the geometry JSON
                try:
                    import json
                    geometry = json.loads(geometry_json) if geometry_json else None
                except Exception as e:
                    logger.warning(f"Failed to parse geometry for county {fips_code}: {e}")
                    continue
                
                if not geometry:
                    continue
                
                feature = {
                    "type": "Feature",
                    "properties": {
                        "fips": fips_code,
                        "county_name": county_name,
                        "state_name": state_name,
                        "value": value,
                        "class": get_class(value)
                    },
                    "geometry": geometry
                }
                features.append(feature)
            
            # Smart unit detection for metadata
            smart_units = ""
            smart_description = ""
            if var == 'premature_death':
                smart_units = "years lost per 100,000"
                smart_description = "Years of potential life lost before age 75 per 100,000 population (age-adjusted)"
            elif var == 'hiv_prevalence':
                smart_units = "per 100,000 population"
                smart_description = "Number of people aged 13 years and older living with a diagnosis of HIV per 100,000 population"
            elif var in ['firearm_fatalities', 'drug_overdose_deaths'] or ('death' in var and 'premature' not in var) or 'mortality' in var:
                smart_units = "per 100,000 population"
                smart_description = "Population-standardized rate"
            elif 'climate' in var:
                smart_units = "0-3 categories"
                smart_description = "Climate threshold categories met"
            elif 'obesity' in var or 'smoking' in var:
                smart_units = "percentage"
                smart_description = "Percentage of adult population"

            # Prepare response with metadata
            response = {
                "type": "FeatureCollection",
                "features": features,
                "metadata": {
                    "variable": var,
                    "display_name": variable_info["display_name"] if variable_info else var.replace("_", " ").title(),
                    "description": variable_info["description"] if (variable_info and variable_info["description"]) else smart_description,
                    "units": variable_info["units"] if (variable_info and variable_info["units"]) else smart_units,
                    "data_type": variable_info["data_type"] if variable_info else "numeric",
                    "total_features": len(features),
                    "class_breaks": breaks,
                    "value_range": {
                        "min": min(values),
                        "max": max(values),
                        "count": len(values)
                    }
                }
            }
            
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting choropleth for {var}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get choropleth data: {str(e)}")


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