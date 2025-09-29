"""
https://github.com/modelcontextprotocol/python-sdk

MCP server
"""

import json
import logging
import os
import sys
import time

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_database, initialize_database
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

mcp = FastMCP("Demo Server")

initialize_database(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
)
db = get_database()


@mcp.resource(name="database_schema", uri="db://schema")
def database_schema():
    try:
        results = db.execute_query(
            """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
                """
        )

        db_schema = {}
        for table in results:
            table_schema = db.execute_query(
                f"""
                SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = '{table['table_name']}';
            """
            )
            db_schema[table["table_name"]] = table_schema

        return {"content": db_schema, "mimeType": "application/json"}
    except Exception as e:
        logger.error(f"Failed to get database schema: {e}")
        raise


@mcp.resource(name="table_list", uri="db://tables")
def table_list():
    """
    Get the database schema for all the tables in the database.
    """
    try:
        results = db.execute_query(
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
            AND table_schema NOT IN ('pg_catalog', 'information_schema');
            """
        )
        return {"content": results, "mimeType": "application/json"}
    except Exception as e:
        logger.error(f"Failed to get database schema: {e}")
        raise


@mcp.tool(name="execute_sql")
def execute_sql(query: str, session_id: int, conversation_id: int, user_id: str = None) -> str:
    """Execute a SQL query on the database.

    Args:
        query: The SQL query to execute
        session_id: The session ID
        conversation_id: The conversation ID
        user_id: The user ID

    Returns:
        JSON string containing the query results
    """
    logger.info("1111111111111session_id: ", session_id)
    logger.info("2222222222222222conversation_id: ", conversation_id)
    logger.info("33333333333333333333333333333user_id: ", user_id)
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    # Basic SQL injection protection - only allow SELECT queries
    if not query.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed for security reasons")

    start_time = time.time()
    status = "SUCCESS"
    error_message = None
    rows_affected = 0
    
    try:
        logger.info(f"Executing query: {query}")
        results = db.execute_query(query)
        execution_time = time.time() - start_time
        rows_affected = len(results) if isinstance(results, list) else 0
        
        logger.info(f"Results Data Type: {type(results)}")
        output_response = {}
        output_response["query"] = query
        output_response["results"] = results
        
        return json.dumps(output_response, default=str)
    except Exception as e:
        execution_time = time.time() - start_time
        status = "ERROR"
        error_message = str(e)
        
        logger.error(f"Query execution failed: {e}")


if __name__ == "__main__":
    mcp.run()