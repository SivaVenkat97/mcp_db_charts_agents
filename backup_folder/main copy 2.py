"""
HTTP Server for MCP Client
Converts the MCP client into streamable HTTP endpoints
"""

import asyncio
import os
import json
import logging
import re
import uvicorn
import traceback

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
logging.basicConfig(
    level=logging.INFO,  # can be DEBUG, INFO, WARNING, ERROR, CRITICAL
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path),  # write to file
        logging.StreamHandler()         # also print to console
    ]
)

logger = logging.getLogger(__name__)

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
        logger.info("Initializing MCP client and agent...")
        await create_mcp_client_and_agent()
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP client/agent: {e}")
        raise
    finally:
        logger.info("Shutting down MCP client...")

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
        logger.error(f"Error creating chat session: {e}")
        return ErrorResponse(
            error=ErrorDetail(
                code="SESSION_CREATION_FAILED",
                message=f"Failed to create chat session: {str(e)}"
            )
        )

# @app.post("/conversations")
# async def create_conversation(request: Request):
#     """Create a new conversation with session_id and question"""
#     try:
#         # Parse JSON payload
#         payload = await request.json()
        
#         # Validate required fields
#         if "session_id" not in payload:
#             return ErrorResponse(
#                 error=ErrorDetail(
#                     code="MISSING_SESSION_ID",
#                     message="session_id is required in the payload"
#                 )
#             )
        
#         if "question" not in payload:
#             return ErrorResponse(
#                 error=ErrorDetail(
#                     code="MISSING_QUESTION",
#                     message="question is required in the payload"
#                 )
#             )
        
#         session_id = payload["session_id"]
#         question = payload["question"]
        
#         # Validate session_id exists in database
#         db = SessionLocal()
#         try:
#             chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
#             if not chat_session:
#                 return ErrorResponse(
#                     error=ErrorDetail(
#                         code="SESSION_NOT_FOUND",
#                         message=f"Chat session with ID {session_id} not found"
#                     )
#                 )
#         finally:
#             db.close()
        
#         # Process the question using MCP agent
#         result, chart_paths = await run_mcp_query(
#             query=question,
#             user_id=None,
#             max_steps=10
#         )
        
#         return SuccessResponse(
#             message="Conversation processed successfully",
#             data={
#                 "session_id": session_id,
#                 "question": question,
#                 "result": result,
#                 "chart_list": chart_paths,
#                 "timestamp": datetime.now().isoformat()
#             }
#         )
        
#     except Exception as e:
#         logger.error(f"Error processing conversation: {e}")
#         return ErrorResponse(
#             error=ErrorDetail(
#                 code="CONVERSATION_PROCESSING_FAILED",
#                 message=f"Failed to process conversation: {str(e)}"
#             )
#         )

async def create_mcp_client_and_agent():
    """Create a new MCP client and agent instance"""
    global mcp_client, mcp_agent
    
    try:
        logger.info("Creating new MCP client and agent...")
        
        # Initialize MCP client with configuration
        config = {
            "mcpServers": {            
                "chart_server": {
                    "command": "python",
                    "args": ["mcp_chart.py"],
                    "transport": {
                        "type": "stdio"
                    }
                },
                "postgres_server": {
                    "command": "python",
                    "args": ["postgres/db_server.py"],
                    "transport": {
                        "type": "stdio"
                    }
                }
            }
        }
        
        mcp_client = MCPClient.from_dict(config)
        logger.info("MCP Client created successfully")
        
        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4o", 
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # System rules
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_rules = f"""
        You are a chart generation assistant. You have access to tools for creating pie charts, bar charts, area charts, line charts, scatter charts, box plots, column charts, dual axis charts, funnel charts, radar charts, sankey charts, tree maps and managing chart images.

        Current Date: {current_date}

        Rules:
        1. Only use tools provided by MCP discovery.
        2. Never invent tool names — only use tools provided by MCP discovery.
        3. Always return structured results from tools. Summarize only if the user specifically asks for a summary.
        4. When users ask to generate pie charts, use the available chart generation tools.
        5. The available tools are:
        - pie_chart: Generate a pie chart from data and save it as PNG
        - bar_chart: Generate a bar chart from data and save it as PNG
        - area_chart: Generate an area chart from data and save it as PNG
        - line_chart: Generate a line chart from data and save it as PNG
        - scatter_chart: Generate a scatter chart from data and save it as PNG
        - box_plot: Generate a box plot from data and save it as PNG
        - column_chart: Generate a column chart from data and save it as PNG
        - dual_axis_chart: Generate a dual axis chart from data and save it as PNG
        - funnel_chart: Generate a funnel chart from data and save it as PNG
        - radar_chart: Generate a radar chart from data and save it as PNG
        - sankey_chart: Generate a sankey chart from data and save it as PNG
        - tree_map: Generate a tree map from data and save it as PNG
        - list_saved_charts: List all saved chart images
        - get_charts_directory: Get the directory where the charts are saved
        - hello_world: Verify the MCP server is responsive
        - execute_sql: Execute a SQL query and return the result
        - database_schema: Get the schema of the database
        - table_list: Get the list of tables in the database

        Available Tools:
        - pie_chart: Use for creating pie charts with data, title, and filename
        - bar_chart: Use for creating horizontal bar charts with data, title, and filename
        - area_chart: Use for creating area charts with data, title, and filename
        - line_chart: Use for creating line charts with data, title, and filename
        - scatter_chart: Use for creating scatter charts with data, title, and filename
        - box_plot: Use for creating box plots with data, title, and filename
        - column_chart: Use for creating column charts with data, title, and filename
        - dual_axis_chart: Use for creating dual axis charts with data, title, and filename
        - funnel_chart: Use for creating funnel charts with data, title, and filename
        - radar_chart: Use for creating radar charts with data, title, and filename
        - sankey_chart: Use for creating sankey charts with data, title, and filename
        - tree_map: Use for creating tree maps with data, title, and filename
        - list_saved_charts: Use for viewing all saved chart images
        - get_charts_directory: Use for getting the directory where the charts are saved
        - hello_world: Use for verifying the MCP server is responsive
        - execute_sql: Use for executing a SQL query and returning the result
        - database_schema: Use for getting the schema of the database
        - table_list: Use for getting the list of tables in the database

        Chart Generation Guidelines:
        - Always provide meaningful titles for charts
        - Use descriptive filenames that reflect the chart content
        - Ensure data is properly formatted as key-value pairs
        - Consider using custom colors for better visual appeal
        - When the user asks a question, always generate multiple relevant charts (not just one) to provide richer insights.
        
        NAMING CONVENTION RULES:
        When the user asks for specific data (e.g., "Show me the list of cars produced in 2021 from the database, and generate all charts from the data"), follow this naming pattern:
        
        1. Extract the main subject/entity from the user's query (e.g., "cars produced in 2021")
        2. For each chart type, create:
           - Title: "[main subject]_[chart type name]" (e.g., "cars produced in 2021_pie chart", "cars produced in 2021_bar chart")
           - Filename: "[main subject with underscores]_[chart type name with underscores].png" (e.g., "cars_produced_in_2021_pie_chart.png", "cars_produced_in_2021_bar_chart.png")
        
        3. Convert spaces to underscores in filenames, keep spaces in titles
        4. Use lowercase for chart type names in filenames, title case for titles
        5. Always include the .png extension in filenames
        
        Examples:
        - Query: "cars produced in 2021" → Title: "cars produced in 2021_line chart", Filename: "cars_produced_in_2021_line_chart.png"
        - Query: "sales data for Q4" → Title: "sales data for Q4_pie chart", Filename: "sales_data_for_q4_pie_chart.png"
        - Query: "employee performance metrics" → Title: "employee performance metrics_scatter chart", Filename: "employee_performance_metrics_scatter_chart.png"

        """

        
        mcp_agent = MCPAgent(llm=llm, client=mcp_client, max_steps=2, system_prompt=system_rules)
        logger.info("MCP Agent created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create MCP client/agent: {e}")
        raise

def extract_chart_paths_from_result(result: Any) -> list:
    """Extract chart paths from MCP agent execution result"""
    chart_paths = []
    
    if isinstance(result, str):
        # Look for file paths in the result string
        # Pattern to match file paths ending with .png
        path_pattern = r'[^\s]+\.png'
        matches = re.findall(path_pattern, result)
        chart_paths.extend(matches)
    
    elif isinstance(result, list):
        # If result is a list, check each item
        for item in result:
            if isinstance(item, str) and item.endswith('.png'):
                chart_paths.append(item)
            elif isinstance(item, dict):
                # Look for path-like values in dictionaries
                for value in item.values():
                    if isinstance(value, str) and value.endswith('.png'):
                        chart_paths.append(value)
    
    elif isinstance(result, dict):
        # Look for path-like values in the dictionary
        for value in result.values():
            if isinstance(value, str) and value.endswith('.png'):
                chart_paths.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.endswith('.png'):
                        chart_paths.append(item)
    
    # Convert absolute paths to relative paths for the media endpoint
    relative_paths = []
    for path in chart_paths:
        if os.path.isabs(path):
            # Convert absolute path to relative path from media directory
            try:
                relative_path = os.path.relpath(path, os.getcwd())
                relative_paths.append(relative_path)
            except ValueError:
                # If conversion fails, use the original path
                relative_paths.append(path)
        else:
            relative_paths.append(path)
    
    # Filter paths to only include those that start with "media"
    media_paths = []
    for path in relative_paths:
        if path.startswith("media/"):
            media_paths.append(path)
    
    return media_paths

async def get_chart_files_from_media() -> list:
    """Get all chart files from the media directory with detailed information"""
    chart_info = []
    try:
        media_dir = "media"
        if os.path.exists(media_dir):
            for root, dirs, files in os.walk(media_dir):
                for file in files:
                    if file.endswith('.png'):
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, os.getcwd())
                        
                        # Get file size
                        file_size = os.path.getsize(full_path)
                        
                        # Extract title from filename (remove extension and convert to title case)
                        title = os.path.splitext(file)[0].replace('_', ' ').replace('-', ' ').title()
                        
                        # Get image dimensions using PIL
                        try:
                            with Image.open(full_path) as img:
                                width, height = img.size
                                # Calculate aspect ratio as a ratio string (e.g., "16:9")
                                if height > 0:
                                    # Find the greatest common divisor to simplify the ratio
                                    def gcd(a, b):
                                        while b:
                                            a, b = b, a % b
                                        return a
                                    divisor = gcd(width, height)
                                    width_ratio = width // divisor
                                    height_ratio = height // divisor
                                    aspect_ratio = f"{width_ratio}:{height_ratio}"
                                else:
                                    aspect_ratio = "1:1"
                        except Exception as img_error:
                            logger.warning(f"Could not get image dimensions for {file}: {img_error}")
                            width, height = 0, 0
                            aspect_ratio = "1:1"
                        
                        chart_info.append({
                            "title": title,
                            "path": relative_path,
                            "size": file_size,
                            "aspect_ratio": aspect_ratio,
                            "width": f"{width}px",
                            "height": f"{height}px"
                        })
    except Exception as e:
        logger.error(f"Error getting chart files: {e}")
    
    # Sort by filename
    return sorted(chart_info, key=lambda x: x["path"])

async def run_mcp_query(query: str, user_id: Optional[str] = None, max_steps: int = 10) -> tuple[Any, list]:
    """Run MCP query and return result along with chart paths"""
    global mcp_agent
    
    # Format user query
    if user_id:
        user_query = f"{query} for user_id '{user_id}'"
    else:
        user_query = query
    
    logger.info(f"Running MCP query: {user_query}")
    
    try:
        # Get chart files before execution
        charts_before = await get_chart_files_from_media()
        
        # Create fresh MCP client and agent for each request to avoid connection issues
        await create_mcp_client_and_agent()
        
        result = await mcp_agent.run(user_query, max_steps=max_steps)

        logger.info("="*100)
        logger.info(f"Result: {result}")
        logger.info("="*100)
        
        # Get chart files after execution
        charts_after = await get_chart_files_from_media()
        
        # Find newly created charts
        new_charts = []
        charts_before_paths = {chart["path"] for chart in charts_before}
        for chart in charts_after:
            if chart["path"] not in charts_before_paths:
                new_charts.append(chart)
        
        return result, new_charts
    except Exception as e:
        logger.error(f"MCP query failed: {e}")
        # Try to recreate client and agent once more
        try:
            logger.info("Attempting to recreate MCP client and agent...")
            await create_mcp_client_and_agent()
            
            # Get chart files before retry
            charts_before_retry = await get_chart_files_from_media()
            
            result = await mcp_agent.run(user_query, max_steps=max_steps)
            
            # Get chart files after retry
            charts_after_retry = await get_chart_files_from_media()
            
            # Find newly created charts from retry
            new_charts = []
            charts_before_retry_paths = {chart["path"] for chart in charts_before_retry}
            for chart in charts_after_retry:
                if chart["path"] not in charts_before_retry_paths:
                    new_charts.append(chart)
            
            return result, new_charts
        except Exception as retry_e:
            logger.error(f"MCP query retry failed: {retry_e}")
            raise HTTPException(
                status_code=500, 
                detail={
                    "status": False,
                    "error": {
                        "code": "QUERY_EXECUTION_FAILED",
                        "message": f"Query execution failed: {str(retry_e)}"
                    }
                }
            )

@app.post("/query")
async def query_mcp(request: QueryRequest):
    """Execute MCP query and return result"""
    try:
        result, chart_paths = await run_mcp_query(
            query=request.query,
            user_id=request.user_id,
            max_steps=request.max_steps
        )
        
        return SuccessResponse(
            message="Query executed successfully",
            data={
                "result": result,
                "chart_list": chart_paths
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
        logger.error(f"Unexpected error in query endpoint: {e}")
        return ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message=f"Unexpected error: {str(e)}"
            )
        )

@app.post("/conversations")
async def create_conversation(request: Request):
    """Create a new conversation with session_id and question"""
    try:
        # Parse JSON payload
        try:
            payload = await request.json()
        except json.JSONDecodeError as json_error:
            logger.error(f"Invalid JSON in request body: {json_error}")
            return ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_JSON",
                    message="Invalid JSON payload. Please check the request body format."
                )
            )
        
        # Validate required fields
        if "session_id" not in payload:
            return ErrorResponse(
                error=ErrorDetail(
                    code="MISSING_SESSION_ID",
                    message="session_id is required in the payload"
                )
            )
        
        if "question" not in payload:
            return ErrorResponse(
                error=ErrorDetail(
                    code="MISSING_QUESTION",
                    message="question is required in the payload"
                )
            )
        
        session_id = payload["session_id"]
        question = payload["question"]
        
        # Validate question is a string type
        if not isinstance(question, str):
            return ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_QUESTION_TYPE",
                    message="please check the question type"
                )
            )
        
        # Validate question is not empty
        if not question or not question.strip():
            return ErrorResponse(
                error=ErrorDetail(
                    code="EMPTY_QUESTION",
                    message="please provide the question"
                )
            )
        
        # Validate session_id exists in database
        db = SessionLocal()
        try:
            chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not chat_session:
                return ErrorResponse(
                    error=ErrorDetail(
                        code="SESSION_NOT_FOUND",
                        message=f"Chat session with ID {session_id} not found"
                    )
                )
            
        finally:
            db.close()
        
        # Get optional parameters
        user_id = payload.get("user_id")
        max_steps = payload.get("max_steps", 10)
        
        async def generate_stream():
            try:
                # Send initial status
                status_response = SuccessResponse(
                    message="Starting conversation...",
                    data={"timestamp": datetime.now().isoformat()}
                )
                yield f"data: {status_response.model_dump_json()}\n\n"
                
                # Execute conversation
                result, chart_paths = await run_mcp_query(
                    query=question,
                    user_id=user_id,
                    max_steps=max_steps
                )
                
                # Store conversation and assets in database
                db = SessionLocal()
                try:
                    # Create conversation record
                    conversation = Conversation(
                        question=question,
                        response=str(result),
                        session_id=session_id
                    )
                    db.add(conversation)
                    db.commit()
                    
                    # Store assets (charts) in database
                    for chart in chart_paths:
                        # Extract title from path
                        title = os.path.splitext(os.path.basename(chart["path"]))[0].replace('_', ' ').replace('-', ' ').title()
                        
                        # Parse width and height from strings like "800px"
                        width = None
                        height = None
                        aspect_ratio = None
                        
                        if chart.get("width") and chart.get("height"):
                            try:
                                # Extract numeric value from strings like "800px"
                                width_str = str(chart["width"]).replace("px", "").strip()
                                height_str = str(chart["height"]).replace("px", "").strip()
                                
                                width = int(width_str) if width_str.isdigit() else None
                                height = int(height_str) if height_str.isdigit() else None
                                
                                # Calculate aspect ratio as float
                                if width and height and height > 0:
                                    aspect_ratio = float(width) / float(height)
                                    
                            except (ValueError, ZeroDivisionError) as e:
                                logger.warning(f"Error parsing dimensions for {chart['path']}: {e}")
                                width = None
                                height = None
                                aspect_ratio = None
                        
                        # If we couldn't parse from width/height, try to parse from aspect_ratio string like "1236:1025"
                        if aspect_ratio is None and chart.get("aspect_ratio"):
                            try:
                                aspect_str = str(chart["aspect_ratio"])
                                if ":" in aspect_str:
                                    parts = aspect_str.split(":")
                                    if len(parts) == 2:
                                        w_ratio = int(parts[0].strip())
                                        h_ratio = int(parts[1].strip())
                                        if h_ratio > 0:
                                            aspect_ratio = float(w_ratio) / float(h_ratio)
                            except (ValueError, ZeroDivisionError) as e:
                                logger.warning(f"Error parsing aspect ratio '{chart.get('aspect_ratio')}' for {chart['path']}: {e}")
                                aspect_ratio = None
                        
                        # Create asset record
                        asset = Asset(
                            title=title,
                            path=chart["path"],
                            width=width,
                            height=height,
                            aspect_ratio=aspect_ratio,
                            session_id=session_id,
                            conversation_id=conversation.id
                        )
                        db.add(asset)


                    
                    db.commit()
                    
                except Exception as db_error:
                    logger.error(f"Database error: {db_error}")
                    db.rollback()
                finally:
                    db.close()
                
                # Send completion
                completion_response = SuccessResponse(
                    message="The Charts have been generated successfully",
                    data={
                        "session_id": session_id,
                        "question": question,
                        "result": result,
                        "chart_list": chart_paths,
                        "timestamp": datetime.now().isoformat()
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
                logger.error(f"Stream error: {e}")
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
        logger.error(f"Error creating conversation: {traceback.format_exc()}")
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
            logger.error(f"Database error creating dashboard: {db_error}")
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
        logger.error(f"Error creating dashboard: {e}")
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
            logger.error(f"Invalid ID format: {ve}")
            return ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_ID_FORMAT",
                    message="Dashboard ID and Asset ID must be valid integers"
                )
            )
        except Exception as db_error:
            logger.error(f"Database error creating dashboard asset association: {db_error}")
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
        logger.error(f"Error creating dashboard asset association: {e}")
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
        logger.error(f"Error creating dashboard asset association: {e}")
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
        logger.error(f"Error listing assets: {e}")
        return ErrorResponse(
            error=ErrorDetail(
                code="LIST_ASSETS_FAILED",
                message=f"Failed to list assets: {str(e)}"
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
        result, chart_paths = await run_mcp_query(
            query=query,
            user_id=user_id,
            max_steps=max_steps
        )
        
        return SuccessResponse(
            message="Query executed successfully",
            data={
                "result": result,
                "chart_list": chart_paths
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
        logger.error(f"Unexpected error in GET query endpoint: {e}")
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
    
    print(f"Starting MCP HTTP Server on {host}:{port}")
    print(f"OpenAPI docs available at: http://{host}:{port}/docs")
    print(f"Health check at: http://{host}:{port}/health")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Disabled auto-reload to stop continuous file watching logs
        log_level="info"
    )
