"""
ETL Pipeline for County Health Explorer.
Loads county health data and spatial geometries into DuckDB.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

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
                conn.execute("""
                    CREATE OR REPLACE VIEW counties_with_geometry AS
                    SELECT 
                        h.*,
                        s.county_name as spatial_county_name,
                        s.state_fp,
                        s.geometry
                    FROM county_health h
                    LEFT JOIN county_spatial s ON h."5-digit FIPS Code" = s.fips_code
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
            health_csv_path: Path to county health CSV file
            spatial_geojson_path: Path to counties GeoJSON file
            
        Returns:
            ETL results and validation summary
        """
        logger.info("Starting full ETL pipeline")
        
        try:
            # Load health data
            health_rows = self.load_county_health_data(health_csv_path)
            
            # Load spatial data
            spatial_rows = self.load_spatial_data(spatial_geojson_path)
            
            # Create joined view
            self.create_joined_view()
            
            # Validate data
            validation_results = self.validate_data()
            
            results = {
                'health_rows_loaded': health_rows,
                'spatial_rows_loaded': spatial_rows,
                'validation': validation_results,
                'success': True
            }
            
            logger.info("ETL pipeline completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}")
            return {
                'success': False,
                'error': str(e)
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


if __name__ == "__main__":
    run_etl() 