from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class PushRequest(BaseModel):
    do_reset: Optional[int] = 0

class SearchRequest(BaseModel):
    text: str
    limit: Optional[int] = 5
    chat_history: Optional[List[Dict[str, Any]]] = None  # Client can send previous chat history