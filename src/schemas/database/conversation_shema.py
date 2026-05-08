from pydantic import BaseModel, Field
from typing import Optional, List
from bson.objectid import ObjectId
from datetime import datetime


class ChatMessageSchema(BaseModel):
    role: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True


class ConversationSchema(BaseModel):
    id: Optional[ObjectId] = Field(None, alias="_id")
    project_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    conversation_id: str = Field(..., min_length=1)
    title: Optional[str] = None
    messages: List[ChatMessageSchema] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def get_indexes(cls):
        return [
            {
                "key": [
                    ("project_id", 1),
                    ("user_id", 1),
                    ("conversation_id", 1),
                ],
                "name": "conversation_unique_index_1",
                "unique": True,
            },
            {
                "key": [
                    ("project_id", 1),
                    ("user_id", 1),
                    ("updated_at", -1),
                ],
                "name": "conversation_project_user_updated_index_1",
                "unique": False,
            },
        ]
