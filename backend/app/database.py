"""
Database module for County Health Explorer.
Handles DuckDB connection with spatial extension.
"""

import duckdb
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Generator

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages DuckDB database connection with spatial extension."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to DuckDB database file. If None, uses in-memory database.
        """
        self.db_path = db_path or ":memory:"
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create database connection with spatial extension."""
        if self._connection is None:
            logger.info(f"Creating DuckDB connection to {self.db_path}")
            self._connection = duckdb.connect(self.db_path)
            self._setup_spatial_extension()
            self._configure_performance()
            
        return self._connection
    
    def _setup_spatial_extension(self):
        """Install and load spatial extension."""
        try:
            logger.info("Setting up DuckDB spatial extension")
            conn = self._connection
            
            # Install spatial extension if not already installed
            conn.execute("INSTALL spatial;")
            
            # Load spatial extension
            conn.execute("LOAD spatial;")
            
            logger.info("Spatial extension loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup spatial extension: {e}")
            raise
    
    def _configure_performance(self):
        """Configure DuckDB for optimal performance."""
        try:
            conn = self._connection
            
            # Set thread count
            conn.execute("SET threads = 4;")
            
            # Set memory limit (4GB)
            conn.execute("SET memory_limit = '4GB';")
            
            logger.info("Database performance configuration applied")
            
        except Exception as e:
            logger.warning(f"Failed to configure performance settings: {e}")
    
    @contextmanager
    def get_cursor(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Context manager for database operations."""
        conn = self.get_connection()
        try:
            yield conn
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            # Connection cleanup is handled by DuckDB automatically
            pass
    
    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    def test_spatial_functionality(self) -> bool:
        """Test if spatial functionality is working."""
        try:
            with self.get_cursor() as conn:
                # Test basic spatial function
                result = conn.execute("""
                    SELECT ST_GeomFromText('POINT(0 0)') as geom
                """).fetchone()
                
                if result:
                    logger.info("Spatial functionality test passed")
                    return True
                    
        except Exception as e:
            logger.error(f"Spatial functionality test failed: {e}")
            
        return False


# Global database manager instance
import os
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "county_health.duckdb")
db_manager = DatabaseManager(db_path)


def get_db() -> DatabaseManager:
    """Get the global database manager instance."""
    return db_manager


def init_database():
    """Initialize database and test functionality."""
    logger.info("Initializing database")
    
    db = get_db()
    
    # Test connection and spatial functionality
    if not db.test_spatial_functionality():
        raise RuntimeError("Failed to initialize spatial functionality")
    
    logger.info("Database initialized successfully")


if __name__ == "__main__":
    # Test the database setup
    logging.basicConfig(level=logging.INFO)
    init_database()
    
    # Test basic operations
    db = get_db()
    with db.get_cursor() as conn:
        # Test spatial query
        result = conn.execute("""
            SELECT 
                ST_AsText(ST_GeomFromText('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))')) as polygon_wkt,
                ST_Area(ST_GeomFromText('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))')) as area
        """).fetchone()
        
        print(f"Test polygon: {result[0]}")
        print(f"Test area: {result[1]}")
    
    db.close() 