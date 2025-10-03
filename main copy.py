"""
HTTP Server for MCP Client
Converts the MCP client into streamable HTTP endpoints
"""

import asyncio
import os
import json
# import logging
import re
import uvicorn
import traceback
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient
from dotenv import load_dotenv
from PIL import Image
from request_response import QueryRequest, ErrorDetail, SuccessResponse, ErrorResponse, Item
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, ChatSession, Conversation, Asset, Dashboard, DashboardAsset

# Create logs folder if it doesn't exist
log_folder = "logs"
os.makedirs(log_folder, exist_ok=True)

# Create a log filename with datetime
log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")
log_path = os.path.join(log_folder, log_filename)

# Configure logging
# logging.basicConfig(
#     level=logging.INFO,  # can be DEBUG, INFO, WARNING, ERROR, CRITICAL
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     handlers=[
#         logging.FileHandler(log_path),  # write to file
#         logging.StreamHandler()         # also print to console
#     ]
# )

# Configure uvicorn logger to be less verbose
# logging.getLogger("uvicorn").setLevel(logging.WARNING)
# logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
# logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
# logging.getLogger("uvicorn.lifespan").setLevel(logging.WARNING)
# logging.getLogger("uvicorn.reload").setLevel(logging.DEBUG)
# logging.getLogger("watchfiles").setLevel(logging.WARNING)

# Add a custom filter to block file watcher messages
# class FileWatcherFilter(logging.Filter):
#     def filter(self, record):
#         # Block messages containing "change detected" or from watchfiles
#         message = record.getMessage()
#         return not ("change detected" in message or "watchfiles" in record.name)

# Apply the filter to the root logger and specific loggers
# root_logger = logging.getLogger()
# root_logger.addFilter(FileWatcherFilter())

# Also apply to uvicorn and watchfiles loggers specifically
# logging.getLogger("uvicorn.reload").addFilter(FileWatcherFilter())
# logging.getLogger("watchfiles").addFilter(FileWatcherFilter())

# logger = logging.getLogger(__name__)

# Global variables for MCP client and agent
mcp_client = None
mcp_agent = None

# Database setup
engine = create_engine("sqlite:///chat_app.db", echo=True)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Load environment variables from .env file
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize MCP client and agent on startup"""
    global mcp_client, mcp_agent
    
    try:
        print("Initializing MCP client and agent...")
        await create_mcp_client_and_agent()
        
        yield
        
    except Exception as e:
        print(f"Failed to initialize MCP client/agent: {e}")
        raise
    finally:
        print("Shutting down MCP client...")

# Create FastAPI app
app = FastAPI(
    title="MCP HTTP Server",
    description="HTTP API wrapper for MCP Client supporting chart generation and PostgreSQL",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the "media" folder so files can be accessed publicly
app.mount("/media", StaticFiles(directory="media"), name="media")

@app.get("/")
async def root():
    """Health check endpoint"""
    return SuccessResponse(
        message="MCP HTTP Server is running",
        data={
            "timestamp": datetime.now().isoformat(),
            "available_endpoints": [
                "/query",
                "/query/stream",
                "/conversations",
                "/chat-sessions",
                "/dashboard",
                "/dashboard-assets",
                "/health",
                "/docs"
            ]
        }
    )


@app.post("/items")
def create_item(item: Item):
    return SuccessResponse(
        message="Item created successfully",
        data={"item_name": item.name}
    )

@app.get("/health")
async def health_check():
    """Health check with MCP client status"""
    global mcp_client, mcp_agent
    
    is_healthy = mcp_client is not None and mcp_agent is not None
    
    if is_healthy:
        return SuccessResponse(
            message="Service is healthy",
            data={
                "mcp_client_initialized": True,
                "mcp_agent_initialized": True,
                "timestamp": datetime.now().isoformat()
            }
        )
    else:
        return ErrorResponse(
            error=ErrorDetail(
                code="SERVICE_UNAVAILABLE",
                message="MCP client or agent not initialized"
            )
        )

@app.get("/chat-sessions")
async def get_chat_sessions():
    """Create a new chat session entry and return the session ID"""
    try:
        # Create database session
        db = SessionLocal()
        
        # Create new chat session
        new_session = ChatSession()
        db.add(new_session)
        db.commit()
        
        return SuccessResponse(
            message="Chat session created successfully",
            data={
                "session_id": new_session.id,
                "created_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        print(f"Error creating chat session: {e}")
        return ErrorResponse(
            error=ErrorDetail(
                code="SESSION_CREATION_FAILED",
                message=f"Failed to create chat session: {str(e)}"
            )
        )

async def create_mcp_client_and_agent():
    """Create a new MCP client and agent instance"""
    global mcp_client, mcp_agent
    
    try:
        print("Creating new MCP client and agent...")
        
        # Initialize MCP client with configuration
        config = {
            "mcpServers": {
                "postgres_server": {
                    "command": "python",
                    "args": ["postgres/db_server.py"],
                    "transport": {
                        "type": "stdio"
                    },
                    # "google_search_console_server": {
                    #     "command": "python",
                    #     "args": ["google_search_console/server.py"],
                    #     "transport": {
                    #         "type": "stdio"
                    #     }
                    # }
                }
            }
        }
        
        mcp_client = MCPClient.from_dict(config)
        print("MCP Client created successfully")
        
        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini", 
            # model="gpt-4o", 
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # System rules
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_rules = f"""
        You are a comprehensive business assistant with access to multiple MCP servers:

        Current Date: {current_date}

        Postgres Database Rules:
        1. Only use SELECT queries with execute_sql.
        2. If the user asks about tables but not columns, prefer table_list.
        3. If the user asks about structure/columns, prefer database_schema.
        4. If you need schema of any table, use database_schema.
        5. Never modify data (INSERT/UPDATE/DELETE not allowed).

        database output format:
        {{{{
            "sql_query": "<the SQL query>",
            "raw_json": <the raw JSON array from the database>,
        }}}}

        Analyze the returned JSON and decide the compatibale chart type(s) for visualization:

        - Use a **Line Chart** if the data represents a continuous trend over time (e.g., dates, months, years).
            Example format:
            [
            {{{{"product": "Laptop", "sales": 120}}}},
            ]
        - Use a **Pie Chart** if the data represents proportions or categories of a whole (e.g., market share, funnel stages).
            Example format:
            [
            {{{{"stage": "Leads", "count": 1000}}}},
            ]
        - Use a **Vertical Bar Chart** if the data compares discrete categories or groups (e.g., product sales, user signups per country).
            Example format:
            [
            {{{{"product": "Laptop", "sales": 120}}}},
            ]

        Prepare a list of one or more chart JSON structures that best represent the given data.
            Each element in the list must include:
            - "type": the chart type (line_chart, pie_chart, vertical_bar_chart)
            - "data": the chart-ready JSON following the formats above.

        Final JSON output format:

            {{{{
            "curl_command": "<the curl command>",
            "sql_query": "<the SQL query>",
            "raw_json": <the raw JSON array from the database>,
            "charts": [
                {{{{
                "type": "<chart_type>",
                "data": <chart_data_array>
                }}}}
            ]
            }}}}

        chart json format rules:
        - Always think step by step before choosing chart type.
        - If multiple chart formats are suitable, include all in the "charts" list.
        - Preserve database column names in the chart data (do not rename them).
        - Ensure the JSON output is strictly valid and parsable.
        - Do not include explanations, text, or markdown outside this JSON.

        """

        
        mcp_agent = MCPAgent(llm=llm, client=mcp_client, max_steps=2, system_prompt=system_rules)
        print("MCP Agent created successfully")
        print("mcp_agent: ", mcp_agent)
        
    except Exception as e:
        print(f"Failed to create MCP client/agent: {traceback.format_exc()}")
        raise



async def run_mcp_query(
        query: str,
        max_steps: int = 10,
        user_id: Optional[str] = None,
        session_id: Optional[int] = 0,
        conversation_id: Optional[int] = 0
    ) -> tuple[Any, list]:

    """Run MCP query and return result along with chart paths"""

    try:

        print("------------------------1")
        print("session_id11: ", session_id)
        print("conversation_id11: ", conversation_id)
        print("------------------------2")


        global mcp_agent
        
        # Format user query
        if user_id:
            user_query = f"{query} for user_id '{user_id}'"
        else:
            user_query = f"{query}, session_id: {session_id}, conversation_id: {conversation_id}"
        
        print(f"Running MCP query: {user_query}")
        print("="*80)
        print("🚀 MCP AGENT EXECUTION STARTED")
        print("="*80)

        # Create fresh MCP client and agent for each request to avoid connection issues
        await create_mcp_client_and_agent()
        
        result = await mcp_agent.run(user_query, max_steps=max_steps)
        print("="*80)
        print("✅ MCP AGENT EXECUTION COMPLETED")
        print(f"📊 Final result: {result}")
        print("="*80)

        print("="*100)
        print(f"Result: {result}")
        print("="*100)

        

        return result
    except Exception as e:
        print(f"MCP query failed: {e}")
        # Try to recreate client and agent once more
        try:
            print("Attempting to recreate MCP client and agent...")
            await create_mcp_client_and_agent()

            
            result = await mcp_agent.run(user_query, max_steps=max_steps)
            print("result111111111111: ", result)
            

            return result
        except Exception as retry_e:
            print(f"MCP query retry failed: {retry_e}")
            print(f"MCP query retry failed: {traceback.format_exc()}")
            raise retry_e




@app.post("/conversations")
async def create_conversation(request: Request):
    """Create a new conversation with session_id and question"""
    try:
        payload = await request.json()
        session_id = payload["session_id"]
        question = payload["question"]

        db = SessionLocal()
        print("111111111111")
        chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not chat_session:
            return ErrorResponse(
                error=ErrorDetail(
                    code="SESSION_NOT_FOUND",
                    message=f"Chat session with ID {session_id} not found"
                )
            )
        print("222222222222")
        
        # Get optional parameters
        user_id = payload.get("user_id")
        max_steps = payload.get("max_steps", 10)
        print("333333333333")

        # Create conversation entry first with just session_id
        conversation_obj = Conversation(session_id=session_id)
        db.add(conversation_obj)
        db.commit()
        print("conversation_obj: ", conversation_obj.id)
        print("444444444444")
      
        async def generate_stream():
            try:
                # Send initial status
                status_response = SuccessResponse(
                    message="Starting conversation...",
                    data={"timestamp": datetime.now().isoformat()}
                )
                yield f"data: {status_response.model_dump_json()}\n\n"

                print("555555555555", conversation_obj.id)
                
                # Execute conversation
                result = await run_mcp_query(
                    query=question,
                    user_id=user_id,
                    max_steps=max_steps,
                    session_id=session_id,
                    conversation_id=conversation_obj.id
                )
                print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
                print("result: ", result)
                print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
                print("666666666666")
                # Update the existing conversation record with question and response
                db = SessionLocal()
                print("777777777777")
                try:
                    # Re-query the conversation object in the new session
                    conversation = db.query(Conversation).filter(Conversation.id == conversation_obj.id).first()
                    if conversation:
                        conversation.question = question
                        conversation.response = str(result)
                        db.commit()
                        print("888888888888")
                    else:
                        print("Conversation not found in database")
                       
                    # Parse the result to extract SQL query and other data
                    sql_query = None
                    raw_json_data = None
                    chart_data = None
                    chart_type = None
                    curl_command = None
                    
                    try:
                        # Try to parse the result as JSON
                        if isinstance(result, str):
                            result_json = json.loads(result)
                            sql_query = result_json.get('sql_query', question) 
                            raw_json_data = json.dumps(result_json.get('raw_json', result)) 
                            curl_command = result_json.get('curl_command', None)                            
                            # Extract chart data if available
                            charts = result_json.get('charts', [])
                            if charts:
                                chart_data=json.dumps(charts)
                                # Extract all chart types, not just the first one
                                chart_types = [chart.get('type') for chart in charts if chart.get('type')]
                                chart_type = ', '.join(chart_types) if chart_types else None
                        else:
                            sql_query = question
                            raw_json_data = str(result)
                            curl_command = None
                    except (json.JSONDecodeError, AttributeError):
                        # If parsing fails, use the original question and result
                        sql_query = question
                        raw_json_data = str(result)
                        curl_command = None
                    # Create asset record with extracted SQL query
                    asset = Asset(
                        session_id=session_id,
                        conversation_id=conversation_obj.id,
                        query=sql_query,
                        raw_json=raw_json_data,
                        chart_data=chart_data,
                        chart_type=chart_type,
                        curl_command=curl_command
                    )
                    db.add(asset)                
                    db.commit()
                    
                except Exception as db_error:
                    print(f"Database error: {db_error}")
                    db.rollback()
                finally:
                    db.close()
                
                # Send completion
                completion_response = SuccessResponse(
                    message="The Charts have been generated successfully",
                    data={
                        "chart_list": result_json.get('charts', None),
                    }
                )
                yield f"data: {completion_response.model_dump_json()}\n\n"
                
            except HTTPException as e:
                error_detail = e.detail
                if isinstance(error_detail, dict) and "error" in error_detail:
                    error_response = ErrorResponse(error=ErrorDetail(**error_detail["error"]))
                else:
                    error_response = ErrorResponse(
                        error=ErrorDetail(
                            code="QUERY_EXECUTION_FAILED",
                            message=str(error_detail)
                        )
                    )
                yield f"data: {error_response.model_dump_json()}\n\n"
            except Exception as e:
                print(f"Stream error: {traceback.format_exc()}")
                error_response = ErrorResponse(
                    error=ErrorDetail(
                        code="INTERNAL_SERVER_ERROR",
                        message=f"Unexpected error: {str(e)}"
                    )
                )
                yield f"data: {error_response.model_dump_json()}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
                                                                                                            
    except Exception as e:
        print(f"Error creating conversation: {traceback.format_exc()}")
        return ErrorResponse(
            error=ErrorDetail(
                code="CONVERSATION_CREATION_FAILED",
                message=f"Failed to create conversation: {str(e)}"
            )
        )

@app.post("/dashboard")
async def create_dashboard(request: Request):
    """Create a new dashboard with a title"""
    try:
        # Parse JSON payload
        payload = await request.json()
        
        # Validate required fields
        if "title" not in payload:
            return ErrorResponse(
                error=ErrorDetail(
                    code="MISSING_TITLE",
                    message="title is required in the payload"
                )
            )
        
        title = payload["title"]
        
        # Validate title is not empty
        if not title or not title.strip():
            return ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_TITLE",
                    message="title cannot be empty"
                )
            )
        
        # Store dashboard in database
        db = SessionLocal()
        try:
            dashboard = Dashboard(title=title.strip())
            db.add(dashboard)
            db.commit()
            
            return SuccessResponse(
                message="Dashboard created successfully",
                data={
                    "dashboard_id": dashboard.id,
                    "title": dashboard.title,
                    "created_at": datetime.now().isoformat()
                }
            )
        except Exception as db_error:
            print(f"Database error creating dashboard: {db_error}")
            db.rollback()
            return ErrorResponse(
                error=ErrorDetail(
                    code="DASHBOARD_CREATION_FAILED",
                    message=f"Failed to create dashboard in database: {str(db_error)}"
                )
            )
        finally:
            db.close()
        
    except json.JSONDecodeError:
        return ErrorResponse(
            error=ErrorDetail(
                code="INVALID_JSON",
                message="Invalid JSON payload"
            )
        )
    except Exception as e:
        print(f"Error creating dashboard: {e}")
        return ErrorResponse(
            error=ErrorDetail(
                code="DASHBOARD_CREATION_FAILED",
                message=f"Failed to create dashboard: {str(e)}"
            )
        )

@app.post("/add-assets")
async def add_assets(request: Request):
    """Create a new dashboard asset association"""
    try:
        # Parse JSON payload
        payload = await request.json()
        
        # Validate required fields
        if "dashboard_id" not in payload:
            return ErrorResponse(
                error=ErrorDetail(
                    code="MISSING_DASHBOARD_ID",
                    message="dashboard_id is required in the payload"
                )
            )
        
        if "asset_id" not in payload:
            return ErrorResponse(
                error=ErrorDetail(
                    code="MISSING_ASSET_ID",
                    message="asset_id is required in the payload"
                )
            )
        
        dashboard_id = payload["dashboard_id"]
        asset_id = payload["asset_id"]
        
        # Validate IDs are not empty
        if not dashboard_id or not dashboard_id.strip():
            return ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_DASHBOARD_ID",
                    message="dashboard_id cannot be empty"
                )
            )
        
        if not asset_id or not asset_id.strip():
            return ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_ASSET_ID",
                    message="asset_id cannot be empty"
                )
            )
        
        # Store dashboard asset association in database
        db = SessionLocal()
        try:
            # Validate that dashboard and asset exist
            dashboard = db.query(Dashboard).filter(Dashboard.id == int(dashboard_id.strip())).first()
            if not dashboard:
                return ErrorResponse(
                    error=ErrorDetail(
                        code="DASHBOARD_NOT_FOUND",
                        message=f"Dashboard with ID {dashboard_id} not found"
                    )
                )
            
            asset = db.query(Asset).filter(Asset.id == int(asset_id.strip())).first()
            if not asset:
                return ErrorResponse(
                    error=ErrorDetail(
                        code="ASSET_NOT_FOUND",
                        message=f"Asset with ID {asset_id} not found"
                    )
                )
            
            # Check if asset is already mapped to this dashboard
            existing_association = db.query(DashboardAsset).filter(
                DashboardAsset.dashboard_id == int(dashboard_id.strip()),
                DashboardAsset.asset_id == int(asset_id.strip())
            ).first()
            
            if existing_association:
                return ErrorResponse(
                    error=ErrorDetail(
                        code="ASSET_ALREADY_MAPPED",
                        message="This asset is already mapped to the dashboard"
                    )
                )
            
            # Create dashboard asset association
            dashboard_asset = DashboardAsset(
                dashboard_id=int(dashboard_id.strip()),
                asset_id=int(asset_id.strip())
            )
            db.add(dashboard_asset)
            db.commit()
            
            return SuccessResponse(
                message="Dashboard asset association created successfully",
                data={
                    "association_id": dashboard_asset.id,
                    "dashboard_id": dashboard_asset.dashboard_id,
                    "asset_id": dashboard_asset.asset_id,
                    "created_at": datetime.now().isoformat()
                }
            )
        except ValueError as ve:
            print(f"Invalid ID format: {ve}")
            return ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_ID_FORMAT",
                    message="Dashboard ID and Asset ID must be valid integers"
                )
            )
        except Exception as db_error:
            print(f"Database error creating dashboard asset association: {db_error}")
            db.rollback()
            return ErrorResponse(
                error=ErrorDetail(
                    code="DASHBOARD_ASSET_CREATION_FAILED",
                    message=f"Failed to create dashboard asset association: {str(db_error)}"
                )
            )
        finally:
            db.close()
        
    except json.JSONDecodeError:
        return ErrorResponse(
            error=ErrorDetail(
                code="INVALID_JSON",
                message="Invalid JSON payload"
            )
        )
    except Exception as e:
        print(f"Error creating dashboard asset association: {e}")
        return ErrorResponse(
            error=ErrorDetail(
                code="DASHBOARD_ASSET_CREATION_FAILED",
                message=f"Failed to create dashboard asset association: {str(e)}"
            )
        )

    except json.JSONDecodeError:
        return ErrorResponse(
            error=ErrorDetail(
                code="INVALID_JSON",
                message="Invalid JSON payload"
            )
        )
    except Exception as e:
        print(f"Error creating dashboard asset association: {e}")
        return ErrorResponse(
            error=ErrorDetail(
                code="DASHBOARD_ASSET_CREATION_FAILED",
                message=f"Failed to create dashboard asset association: {str(e)}"
            )
        )

@app.post("/list_assests")
async def list_assests(request: Request):
    """List assets associated with a dashboard by dashboard_id"""
    try:
        payload = await request.json()

        if "dashboard_id" not in payload:
            return ErrorResponse(
                error=ErrorDetail(
                    code="MISSING_DASHBOARD_ID",
                    message="dashboard_id is required in the payload"
                )
            )

        dashboard_id = payload["dashboard_id"]

        if dashboard_id is None or (isinstance(dashboard_id, str) and not dashboard_id.strip()):
            return ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_DASHBOARD_ID",
                    message="dashboard_id cannot be empty"
                )
            )

        try:
            dashboard_id_int = int(str(dashboard_id).strip())
        except ValueError:
            return ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_ID_FORMAT",
                    message="dashboard_id must be a valid integer"
                )
            )

        db = SessionLocal()
        try:
            dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id_int).first()
            if not dashboard:
                return ErrorResponse(
                    error=ErrorDetail(
                        code="DASHBOARD_NOT_FOUND",
                        message=f"Dashboard with ID {dashboard_id_int} not found"
                    )
                )

            # Collect assets via association table
            assest_list = []
            for assoc in dashboard.assets:
                asset = db.query(Asset).filter(Asset.id == assoc.asset_id).first()
                if not asset:
                    continue
                assest_list.append({
                    "title": asset.title,
                    "path": asset.path,
                    "width": asset.width,
                    "height": asset.height,
                    "aspect_ratio": asset.aspect_ratio
                })

            return SuccessResponse(
                message="Assets fetched successfully",
                data={
                    "dashboard_id": dashboard.id,
                    "dashboard_title": dashboard.title,
                    "assest_list": assest_list
                }
            )
        finally:
            db.close()

    except json.JSONDecodeError:
        return ErrorResponse(
            error=ErrorDetail(
                code="INVALID_JSON",
                message="Invalid JSON payload"
            )
        )
    except Exception as e:
        print(f"Error listing assets: {e}")
        return ErrorResponse(
            error=ErrorDetail(
                code="LIST_ASSETS_FAILED",
                message=f"Failed to list assets: {str(e)}"
            )
        )

@app.post("/query")
async def query_mcp(request: QueryRequest):
    """Execute MCP query and return result"""
    try:
        result = await run_mcp_query(
            query=request.query,
            user_id=request.user_id,
            max_steps=request.max_steps
        )
        
        return SuccessResponse(
            message="Query executed successfully",
            data={
                "result": result,
                # "chart_list": chart_paths
            }
        )
        
    except HTTPException as e:
        # Extract error details from HTTPException
        error_detail = e.detail
        if isinstance(error_detail, dict) and "error" in error_detail:
            return ErrorResponse(error=ErrorDetail(**error_detail["error"]))
        else:
            return ErrorResponse(
                error=ErrorDetail(
                    code="QUERY_EXECUTION_FAILED",
                    message=str(error_detail)
                )
            )
    except Exception as e:
        print(f"Unexpected error in query endpoint: {e}")
        return ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message=f"Unexpected error: {str(e)}"
            )
        )

@app.get("/query")
async def query_mcp_get(
    query: str = Query(..., description="Query string for operations"),
    user_id: Optional[str] = Query(None, description="User ID for operations"),
    max_steps: int = Query(10, description="Maximum steps for agent execution")
):
    """Execute MCP query via GET request"""
    try:
        result = await run_mcp_query(
            query=query,
            user_id=user_id,
            max_steps=max_steps
        )
        
        return SuccessResponse(
            message="Query executed successfully",
            data={
                "result": result,
                # "chart_list": chart_paths
            }
        )
        
    except HTTPException as e:
        # Extract error details from HTTPException
        error_detail = e.detail
        if isinstance(error_detail, dict) and "error" in error_detail:
            return ErrorResponse(error=ErrorDetail(**error_detail["error"]))
        else:
            return ErrorResponse(
                error=ErrorDetail(
                    code="QUERY_EXECUTION_FAILED",
                    message=str(error_detail)
                )
            )
    except Exception as e:
        print(f"Unexpected error in GET query endpoint: {e}")
        return ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message=f"Unexpected error: {str(e)}"
            )
        )

if __name__ == "__main__":
    
    # Get port from environment variable or default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    # print(f"Starting MCP HTTP Server on {host}:{port}")
    # print(f"OpenAPI docs available at: http://{host}:{port}/docs")
    # print(f"Health check at: http://{host}:{port}/health")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,  # Disabled auto-reload to stop continuous file watching logs
    )
