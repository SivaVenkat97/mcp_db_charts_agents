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
from models import SqlQuery, ChatSession, Conversation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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

# Create SQLite engine for storing SQL queries
sqlite_engine = create_engine("sqlite:///chat_app.db", echo=False)
SqlSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)

def store_sql_query_in_main_db(
    query: str,
    query_type: str = None,
    execution_time: float = None,
    rows_affected: int = None,
    status: str = "SUCCESS",
    error_message: str = None,
    session_id: int = None,
    conversation_id: int = None,
    user_id: str = None
) -> int:
    """Store SQL query in the main SQLite database"""
    db_session = SqlSessionLocal()
    try:
        # Determine query type if not provided
        if not query_type:
            query_upper = query.strip().upper()
            if query_upper.startswith('SELECT'):
                query_type = 'SELECT'
            elif query_upper.startswith('INSERT'):
                query_type = 'INSERT'
            elif query_upper.startswith('UPDATE'):
                query_type = 'UPDATE'
            elif query_upper.startswith('DELETE'):
                query_type = 'DELETE'
            elif query_upper.startswith('CREATE'):
                query_type = 'CREATE'
            elif query_upper.startswith('DROP'):
                query_type = 'DROP'
            elif query_upper.startswith('ALTER'):
                query_type = 'ALTER'
            else:
                query_type = 'OTHER'
        
        sql_query = SqlQuery(
            query=query,
            query_type=query_type,
            execution_time=execution_time,
            rows_affected=rows_affected,
            status=status,
            error_message=error_message,
            session_id=session_id,
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        db_session.add(sql_query)
        db_session.commit()
        
        logger.info(f"Stored SQL query in main DB: {query[:100]}... (ID: {sql_query.id})")
        return sql_query.id
        
    except Exception as e:
        logger.error(f"Error storing SQL query in main DB: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


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
def execute_sql(query: str) -> str:
    """Execute a SQL query on the database.

    Args:
        query: The SQL query to execute

    Returns:
        JSON string containing the query results
    """
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
        
        # Store the SQL query in the main database
        try:
            store_sql_query_in_main_db(
                query=query,
                query_type="SELECT",
                execution_time=execution_time,
                rows_affected=rows_affected,
                status=status,
                error_message=error_message
            )
        except Exception as store_error:
            logger.error(f"Failed to store SQL query in main DB: {store_error}")
            # Don't fail the main query if storage fails
        
        return json.dumps(output_response, default=str)
    except Exception as e:
        execution_time = time.time() - start_time
        status = "ERROR"
        error_message = str(e)
        
        logger.error(f"Query execution failed: {e}")
        
        # Store the failed SQL query in the main database
        try:
            store_sql_query_in_main_db(
                query=query,
                query_type="SELECT",
                execution_time=execution_time,
                rows_affected=0,
                status=status,
                error_message=error_message
            )
        except Exception as store_error:
            logger.error(f"Failed to store failed SQL query in main DB: {store_error}")
        
        raise


if __name__ == "__main__":
    mcp.run()