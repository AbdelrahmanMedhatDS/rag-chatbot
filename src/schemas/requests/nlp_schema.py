from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union

class PushRequest(BaseModel):
    do_reset: Optional[int] = 0
    index_only_new: Optional[bool] = True

class SearchRequest(BaseModel):
    text: str
    limit: Optional[int] = 5
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    use_memory: Optional[bool] = True
    enable_query_rewrite: Optional[bool] = True
    chat_history: Optional[List[Dict[str, Any]]] = None  # Client can send previous chat history


class ConversationCreateRequest(BaseModel):
    user_id: str
    conversation_id: Optional[str] = None


class ConversationListRequest(BaseModel):
    user_id: str
    page: Optional[int] = 1
    page_size: Optional[int] = 20


class VectorInspectRequest(BaseModel):
    limit: Optional[int] = 50
    offset: Optional[Union[str, int]] = None
    include_vectors: Optional[bool] = True


class VectorDuplicatesRequest(BaseModel):
    limit: Optional[int] = 5000
    offset: Optional[Union[str, int]] = None
    min_count: Optional[int] = 2
    max_groups: Optional[int] = 100