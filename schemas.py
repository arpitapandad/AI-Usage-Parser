from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional, Dict, Any

class CanonicalEvent(BaseModel):
    """The single canonical shape for all AI usage events"""
    
    event_id: str
    timestamp: datetime
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    tool: Literal["openai", "anthropic", "cursor", "other"]
    action: str  # e.g., "chat_completion", "embedding"
    
    # Request details
    prompt: Optional[str] = None
    request_model: Optional[str] = None
    
    # Response details
    response_content: Optional[str] = None
    response_model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    
    # Cost & status (can be backfilled later)
    cost_estimate: Optional[float] = None
    status: Literal["complete", "partial", "error"]
    
    # For debugging and replay
    raw_url: str
    raw_payload_hash: str
    metadata: Dict[str, Any] = {}

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }