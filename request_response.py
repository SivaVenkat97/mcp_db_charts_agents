"""
API Request/Response models for HTTP endpoints
"""

from typing import Optional, Any
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    max_steps: int = 10


class ErrorDetail(BaseModel):
    code: str
    message: str


class SuccessResponse(BaseModel):
    status: bool = True
    message: str
    data: Any


class ErrorResponse(BaseModel):
    status: bool = False
    error: ErrorDetail


class Item(BaseModel):
    name: str


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None
    user_id: Optional[str] = None


class ChatSessionResponse(BaseModel):
    id: int
    title: Optional[str] = None
    user_id: Optional[str] = None
    created_at: Optional[str] = None
