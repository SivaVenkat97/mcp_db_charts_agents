import logging
import os
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """PostgreSQL database connection manager with simple connections."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None,
    ):
        """
        Initialize database connection parameters.

        Args:
            host: Database host (defaults to environment variable POSTGRES_HOST or 'localhost')
            port: Database port (defaults to environment variable POSTGRES_PORT or 5432)
            database: Database name (defaults to environment variable POSTGRES_DB or 'postgres')
            user: Database user (defaults to environment variable POSTGRES_USER or 'postgres')
            password: Database password (defaults to environment variable POSTGRES_PASSWORD)
        """
        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.port = port or int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = database or os.getenv("POSTGRES_DB", "postgres")
        self.user = user or os.getenv("POSTGRES_USER", "postgres")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "")
        
        logger.info(
            f"Database connection configured for database '{self.database}' on {self.host}:{self.port}"
        )

    def get_connection(self):
        """Get a new database connection."""
        try:
            connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor,
            )
            logger.debug("New database connection created")
            return connection
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise

    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            List of dictionaries containing query results
        """
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            cursor.execute(query, params)
            results = cursor.fetchall()

            # Convert RealDictRow objects to regular dictionaries
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def execute_command(self, command: str, params: tuple = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE command.

        Args:
            command: SQL command string
            params: Command parameters (optional)

        Returns:
            Number of affected rows
        """
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            cursor.execute(command, params)
            affected_rows = cursor.rowcount

            connection.commit()
            logger.info(f"Command executed successfully. {affected_rows} rows affected.")

            return affected_rows

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def test_connection(self) -> bool:
        """Test the database connection."""
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

            if result and result[0] == 1:
                logger.info("Database connection test successful")
                return True
            else:
                logger.error("Database connection test failed")
                return False

        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()


# Global database instance
db = None


def initialize_database(**kwargs) -> DatabaseConnection:
    """
    Initialize the global database connection.

    Args:
        **kwargs: Database connection parameters

    Returns:
        DatabaseConnection instance
    """
    global db
    if db is None:
        db = DatabaseConnection(**kwargs)
    return db


def get_database() -> DatabaseConnection:
    """Get the global database instance."""
    if db is None:
        raise Exception("Database not initialized. Call initialize_database() first.")
    return db


# Example usage and connection test
if __name__ == "__main__":
    try:
        # Initialize database connection
        db_conn = initialize_database()

        # Test connection
        if db_conn.test_connection():
            print("✅ Database connection successful!")

            # Example query
            results = db_conn.execute_query("SELECT version()")
            print(f"PostgreSQL version: {results[0]['version']}")

        else:
            print("❌ Database connection failed!")

    except Exception as e:
        print(f"❌ Error: {e}")