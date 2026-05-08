from pydantic import BaseModel, Field, field_validator
from typing import Optional
from bson import ObjectId
from datetime import datetime

class ChunkSchema(BaseModel):
    id : Optional[ObjectId] = Field(None, alias="_id")
    chunk_text: str = Field(..., min_length=1)
    chunk_metadata: dict
    chunk_order: int = Field(..., gt=0)
    chunk_project_id: ObjectId
    chunk_asset_id: Optional[ObjectId] = None
    chunk_is_indexed: bool = Field(default=False)
    chunk_indexed_at: Optional[datetime] = None
    chunk_is_processing: bool = Field(default=False)
    chunk_processing_at: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True



    @classmethod
    def get_indexes(cls):
        
        return [
            {
                "key": [
                    ("chunk_project_id", 1)
                ],
                "name": "chunk_project_id_index_1",
                "unique": False
            },
            {
                "key": [
                    ("chunk_project_id", 1),
                    ("chunk_is_indexed", 1)
                ],
                "name": "chunk_project_id_indexed_index_1",
                "unique": False
            },
            {
                "key": [
                    ("chunk_project_id", 1),
                    ("chunk_is_indexed", 1),
                    ("chunk_is_processing", 1),
                    ("chunk_processing_at", 1)
                ],
                "name": "chunk_project_id_lock_index_1",
                "unique": False
            }
        ]
    

class RetrievedDocumentSchema(BaseModel):
    score : float
    text : str