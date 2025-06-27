"""
ETL Pipeline for County Health Explorer.
Loads county health data and spatial geometries into DuckDB.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import geopandas as gpd
import duckdb

from .database import get_db, DatabaseManager

logger = logging.getLogger(__name__)


class CountyHealthETL:
    """ETL pipeline for county health and spatial data."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize ETL pipeline.
        
        Args:
            db_manager: Database manager instance. If None, uses global instance.
        """
        self.db = db_manager or get_db()
        
    def load_county_health_data(self, csv_path: str) -> int:
        """
        Load county health data from CSV into DuckDB.
        
        Args:
            csv_path: Path to the county health CSV file
            
        Returns:
            Number of rows loaded
        """
        logger.info(f"Loading county health data from {csv_path}")
        
        try:
            with self.db.get_cursor() as conn:
                # Use DuckDB's read_csv_auto function for efficient loading
                conn.execute(f"""
                    CREATE OR REPLACE TABLE county_health AS 
                    SELECT * FROM read_csv_auto('{csv_path}', header=true)
                """)
                
                # Get row count
                result = conn.execute("SELECT COUNT(*) FROM county_health").fetchone()
                row_count = result[0] if result else 0
                
                logger.info(f"Loaded {row_count} rows of county health data")
                return row_count
                
        except Exception as e:
            logger.error(f"Failed to load county health data: {e}")
            raise
    
    def load_spatial_data(self, geojson_path: str) -> int:
        """
        Load county spatial data from GeoJSON into DuckDB.
        
        Args:
            geojson_path: Path to the counties GeoJSON file
            
        Returns:
            Number of counties loaded
        """
        logger.info(f"Loading spatial data from {geojson_path}")
        
        try:
            # Read GeoJSON file
            with open(geojson_path, 'r') as f:
                geojson_data = json.load(f)
            
            features = geojson_data.get('features', [])
            logger.info(f"Found {len(features)} features in GeoJSON")
            
            # Process features and convert to format suitable for DuckDB
            spatial_records = []
            
            for feature in features:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                
                # Extract key properties
                fips_code = properties.get('GEOID', '')
                county_name = properties.get('NAME', '')
                state_fp = properties.get('STATEFP', '')
                
                # Convert geometry to WKT format for DuckDB spatial
                geometry_wkt = self._geometry_to_wkt(geometry)
                
                if fips_code and geometry_wkt:
                    spatial_records.append({
                        'fips_code': fips_code,
                        'county_name': county_name,
                        'state_fp': state_fp,
                        'geometry_wkt': geometry_wkt
                    })
            
            # Load into DuckDB
            with self.db.get_cursor() as conn:
                # Create spatial table
                conn.execute("""
                    CREATE OR REPLACE TABLE county_spatial (
                        fips_code VARCHAR,
                        county_name VARCHAR,
                        state_fp VARCHAR,
                        geometry GEOMETRY
                    )
                """)
                
                # Insert spatial data
                for record in spatial_records:
                    conn.execute("""
                        INSERT INTO county_spatial (fips_code, county_name, state_fp, geometry)
                        VALUES (?, ?, ?, ST_GeomFromText(?))
                    """, [
                        record['fips_code'],
                        record['county_name'], 
                        record['state_fp'],
                        record['geometry_wkt']
                    ])
                
                # Create spatial index for performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_county_spatial_geom 
                    ON county_spatial USING RTREE (geometry)
                """)
                
                # Create index on FIPS code for joins
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_county_spatial_fips 
                    ON county_spatial (fips_code)
                """)
                
                logger.info(f"Loaded {len(spatial_records)} spatial records")
                return len(spatial_records)
                
        except Exception as e:
            logger.error(f"Failed to load spatial data: {e}")
            raise
    
    def _geometry_to_wkt(self, geometry: Dict[str, Any]) -> Optional[str]:
        """
        Convert GeoJSON geometry to WKT format.
        
        Args:
            geometry: GeoJSON geometry object
            
        Returns:
            WKT string representation of geometry
        """
        try:
            geom_type = geometry.get('type', '')
            coordinates = geometry.get('coordinates', [])
            
            if geom_type == 'Polygon':
                return self._polygon_to_wkt(coordinates)
            elif geom_type == 'MultiPolygon':
                return self._multipolygon_to_wkt(coordinates)
            else:
                logger.warning(f"Unsupported geometry type: {geom_type}")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to convert geometry to WKT: {e}")
            return None
    
    def _polygon_to_wkt(self, coordinates) -> str:
        """Convert polygon coordinates to WKT."""
        rings = []
        for ring in coordinates:
            ring_coords = [f"{coord[0]} {coord[1]}" for coord in ring]
            rings.append(f"({', '.join(ring_coords)})")
        
        return f"POLYGON({', '.join(rings)})"
    
    def _multipolygon_to_wkt(self, coordinates) -> str:
        """Convert multipolygon coordinates to WKT."""
        polygons = []
        for polygon in coordinates:
            rings = []
            for ring in polygon:
                ring_coords = [f"{coord[0]} {coord[1]}" for coord in ring]
                rings.append(f"({', '.join(ring_coords)})")
            polygons.append(f"({', '.join(rings)})")
        
        return f"MULTIPOLYGON({', '.join(polygons)})"
    
    def create_joined_view(self):
        """Create a view that joins health data with spatial data."""
        logger.info("Creating joined view of health and spatial data")
        
        try:
            with self.db.get_cursor() as conn:
                # First, let's identify and cast numeric columns properly
                columns_result = conn.execute("DESCRIBE county_health").fetchall()
                
                # Build a list of columns with proper casting for numeric raw value columns
                column_selects = []
                for col_name, col_type in columns_result:
                    if "raw value" in col_name:
                        # Cast raw value columns to DOUBLE for proper numeric operations
                        column_selects.append(f'CAST("{col_name}" AS DOUBLE) AS "{col_name}"')
                    elif col_name in ['5-digit FIPS Code', 'Name', 'State Abbreviation']:
                        # Keep key string columns
                        column_selects.append(f'"{col_name}"')
                    else:
                        # Keep other columns as-is
                        column_selects.append(f'"{col_name}"')
                
                # Create the properly typed view
                conn.execute(f"""
                    CREATE OR REPLACE VIEW county_health_joined AS
                    SELECT 
                        h."5-digit FIPS Code" as fips_code,
                        h."Name" as county_name,
                        h."State Abbreviation" as state_name,
                        {", ".join([f'h.{col}' for col in column_selects])},
                        s.geometry
                    FROM county_health h
                    INNER JOIN county_spatial s ON h."5-digit FIPS Code" = s.fips_code
                    WHERE s.geometry IS NOT NULL
                """)
                
                # Create an alternative simpler view for quick access
                conn.execute("""
                    CREATE OR REPLACE VIEW counties_with_geometry AS
                    SELECT 
                        h."5-digit FIPS Code" as fips_code,
                        h."Name" as county_name,
                        h."State Abbreviation" as state_name,
                        CAST(h."Firearm Fatalities raw value" AS DOUBLE) as firearm_fatalities,
                        CAST(h."Adverse Climate Events raw value" AS DOUBLE) as adverse_climate_events,
                        CAST(h."Adult Obesity raw value" AS DOUBLE) as adult_obesity,
                        CAST(h."Premature Death raw value" AS DOUBLE) as premature_death,
                        CAST(h."Poor Physical Health Days raw value" AS DOUBLE) as poor_physical_health_days,
                        CAST(h."Poor Mental Health Days raw value" AS DOUBLE) as poor_mental_health_days,
                        s.geometry
                    FROM county_health h
                    INNER JOIN county_spatial s ON h."5-digit FIPS Code" = s.fips_code
                    WHERE s.geometry IS NOT NULL
                """)
                
                logger.info("Created counties_with_geometry view")
                
        except Exception as e:
            logger.error(f"Failed to create joined view: {e}")
            raise
    
    def validate_data(self) -> Dict[str, Any]:
        """
        Validate loaded data quality and completeness.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating loaded data")
        
        validation_results = {}
        
        try:
            with self.db.get_cursor() as conn:
                # Count health records
                result = conn.execute("SELECT COUNT(*) FROM county_health").fetchone()
                health_count = result[0] if result else 0
                
                # Count spatial records
                result = conn.execute("SELECT COUNT(*) FROM county_spatial").fetchone()
                spatial_count = result[0] if result else 0
                
                # Count joined records
                result = conn.execute("""
                    SELECT COUNT(*) FROM counties_with_geometry 
                    WHERE geometry IS NOT NULL
                """).fetchone()
                joined_count = result[0] if result else 0
                
                # Check for missing geometries
                result = conn.execute("""
                    SELECT COUNT(*) FROM counties_with_geometry 
                    WHERE geometry IS NULL
                """).fetchone()
                missing_geometries = result[0] if result else 0
                
                # Check for duplicate FIPS codes
                result = conn.execute("""
                    SELECT COUNT(*) - COUNT(DISTINCT "5-digit FIPS Code") as duplicates
                    FROM county_health
                """).fetchone()
                duplicate_fips = result[0] if result else 0
                
                validation_results = {
                    'health_records': health_count,
                    'spatial_records': spatial_count,
                    'joined_records': joined_count,
                    'missing_geometries': missing_geometries,
                    'duplicate_fips': duplicate_fips,
                    'join_success_rate': (joined_count / health_count * 100) if health_count > 0 else 0
                }
                
                # Log validation results
                logger.info(f"Validation results: {validation_results}")
                
                # Check if we have expected number of counties (~3,142)
                expected_counties = 3142
                if health_count < expected_counties * 0.95:  # Allow 5% tolerance
                    logger.warning(f"Health records ({health_count}) below expected (~{expected_counties})")
                
                if missing_geometries > health_count * 0.05:  # More than 5% missing
                    logger.warning(f"High number of missing geometries: {missing_geometries}")
                
                return validation_results
                
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            raise
    
    def run_full_etl(self, health_csv_path: str, spatial_geojson_path: str) -> Dict[str, Any]:
        """
        Run the complete ETL pipeline.
        
        Args:
            health_csv_path: Path to health data CSV
            spatial_geojson_path: Path to spatial GeoJSON
            
        Returns:
            Dictionary with ETL results and validation metrics
        """
        logger.info("Starting full ETL pipeline")
        
        try:
            results = {}
            
            # Step 1: Load health data
            logger.info("Step 1: Loading health data")
            health_rows = self.load_county_health_data(health_csv_path)
            results['health_rows_loaded'] = health_rows
            
            # Step 2: Load spatial data
            logger.info("Step 2: Loading spatial data")
            spatial_rows = self.load_spatial_data(spatial_geojson_path)
            results['spatial_rows_loaded'] = spatial_rows
            
            # Step 3: Create joined view
            logger.info("Step 3: Creating joined view")
            self.create_joined_view()
            
            # Step 4: Load variable metadata
            logger.info("Step 4: Loading variable metadata")
            data_dir = Path(health_csv_path).parent
            metadata = load_variable_metadata(data_dir)
            
            with self.db.get_cursor() as conn:
                create_metadata_table(conn, metadata)
            
            results['metadata_vars_loaded'] = len(metadata)
            
            # Step 5: Validate results
            logger.info("Step 5: Validating ETL results")
            validation = self.validate_data()
            results['validation'] = validation
            
            # Step 6: Final success check
            if validation['join_success_rate'] < 90:
                logger.warning(f"Low join success rate: {validation['join_success_rate']:.1f}%")
            
            results['success'] = True
            logger.info("ETL pipeline completed successfully")
            
            return results
            
        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'health_rows_loaded': results.get('health_rows_loaded', 0),
                'spatial_rows_loaded': results.get('spatial_rows_loaded', 0),
                'metadata_vars_loaded': results.get('metadata_vars_loaded', 0)
            }


def run_etl():
    """Main function to run ETL pipeline with default paths."""
    logging.basicConfig(level=logging.INFO)
    
    etl = CountyHealthETL()
    
    # Default file paths
    health_csv = "data/analytic_data2025_v2.csv"
    spatial_geojson = "data/counties.json"
    
    # Check if files exist
    if not Path(health_csv).exists():
        raise FileNotFoundError(f"Health data file not found: {health_csv}")
    
    if not Path(spatial_geojson).exists():
        raise FileNotFoundError(f"Spatial data file not found: {spatial_geojson}")
    
    # Run ETL
    results = etl.run_full_etl(health_csv, spatial_geojson)
    
    if results['success']:
        print("ETL Pipeline Results:")
        print(f"  Health records loaded: {results['health_rows_loaded']}")
        print(f"  Spatial records loaded: {results['spatial_rows_loaded']}")
        print(f"  Join success rate: {results['validation']['join_success_rate']:.1f}%")
        print(f"  Missing geometries: {results['validation']['missing_geometries']}")
    else:
        print(f"ETL failed: {results['error']}")
    
    return results


def load_variable_metadata(data_dir: Path) -> Dict[str, Dict[str, str]]:
    """
    Load variable metadata from DataDictionary_2025.csv.
    
    Returns:
        Dictionary mapping variable codes to metadata (description, units, etc.)
    """
    logger.info("Loading variable metadata from data dictionary")
    
    dict_path = data_dir / "DataDictionary_2025.csv"
    if not dict_path.exists():
        logger.warning(f"Data dictionary not found at {dict_path}")
        return {}
    
    try:
        df = pd.read_csv(dict_path)
        logger.info(f"Loaded data dictionary with {len(df)} entries")
        
        metadata = {}
        
        for _, row in df.iterrows():
            var_name = row['Variable Name']
            description = row['Description']
            measure = row.get('Measure', '')
            
            # Only process raw value variables
            if 'rawvalue' in var_name:
                # Extract base variable code (e.g., v001 from v001_rawvalue)
                var_code = var_name.split('_')[0]
                
                # Determine units and data type from description
                units = extract_units_from_description(description)
                data_type = determine_data_type(description)
                
                # Clean up the description
                clean_description = description.strip()
                if clean_description.endswith('.'):
                    clean_description = clean_description[:-1]
                
                metadata[var_code] = {
                    'description': clean_description,
                    'measure': measure.strip() if measure else '',
                    'units': units,
                    'data_type': data_type,
                    'raw_variable': var_name,
                    'measure_name': measure.strip() if measure else ''
                }
        
        logger.info(f"Processed metadata for {len(metadata)} health variables")
        return metadata
        
    except Exception as e:
        logger.error(f"Failed to load variable metadata: {e}")
        return {}


def extract_units_from_description(description: str) -> str:
    """Extract units from a variable description."""
    description = description.lower()
    
    # Common unit patterns
    if 'per 100,000' in description:
        return 'per 100,000 population'
    elif 'per 1,000' in description:
        return 'per 1,000 population'
    elif 'per 10,000' in description:
        return 'per 10,000 population'
    elif 'percentage' in description or 'percent' in description:
        return 'percentage'
    elif 'years' in description and 'life' in description:
        return 'years'
    elif 'days' in description:
        return 'days'
    elif 'ratio' in description:
        return 'ratio'
    elif 'index' in description:
        return 'index'
    elif 'number of' in description and 'per' not in description:
        return 'count'
    elif 'rate' in description:
        return 'rate'
    else:
        return 'numeric'


def determine_data_type(description: str) -> str:
    """Determine the appropriate data type category."""
    description = description.lower()
    
    if any(term in description for term in ['death', 'mortality', 'fatalities', 'life expectancy']):
        return 'mortality'
    elif any(term in description for term in ['percentage', 'percent']):
        return 'percentage'
    elif any(term in description for term in ['rate', 'per 100,000', 'per 1,000']):
        return 'rate'
    elif any(term in description for term in ['income', 'dollar']):
        return 'currency'
    elif 'index' in description:
        return 'index'
    elif 'ratio' in description:
        return 'ratio'
    else:
        return 'numeric'


def create_metadata_table(conn: duckdb.DuckDBPyConnection, metadata: Dict[str, Dict[str, str]]):
    """Create and populate the variable metadata table."""
    logger.info("Creating variable metadata table")
    
    # Drop and recreate the table to ensure proper schema
    conn.execute("DROP TABLE IF EXISTS variable_metadata")
    
    # Create the table
    conn.execute("""
        CREATE TABLE variable_metadata (
            variable_code VARCHAR PRIMARY KEY,
            display_name VARCHAR,
            description TEXT,
            measure VARCHAR,
            units VARCHAR,
            data_type VARCHAR,
            raw_variable VARCHAR,
            measure_name VARCHAR
        )
    """)
    
    # Insert metadata
    for var_code, meta in metadata.items():
        # Create display name from description
        display_name = create_display_name(meta['description'])
        
        conn.execute("""
            INSERT INTO variable_metadata 
            (variable_code, display_name, description, measure, units, data_type, raw_variable, measure_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            var_code,
            display_name,
            meta['description'],
            meta['measure'],
            meta['units'],
            meta['data_type'],
            meta['raw_variable'],
            meta['measure_name']
        ])
    
    logger.info(f"Inserted metadata for {len(metadata)} variables")


def create_display_name(description: str) -> str:
    """Create a clean display name from the description."""
    # Take the first part of the description, usually the main concept
    parts = description.split('.')
    if len(parts) > 1:
        # Use the first sentence if it's descriptive enough
        first_part = parts[0].strip()
        if len(first_part) > 10:
            return first_part
    
    # Otherwise use the full description, truncated if too long
    if len(description) > 60:
        return description[:57] + "..."
    
    return description


if __name__ == "__main__":
    run_etl() 