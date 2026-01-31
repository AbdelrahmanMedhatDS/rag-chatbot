from pydantic import BaseModel, Field, field_validator
from bson import ObjectId
from typing import Optional


class ProjectSchema(BaseModel):
    id : Optional[ObjectId] = Field(None, alias="_id")
    project_id: str = Field(..., min_length=1)  

    # manual validator if the support of Field is not enough ( designed validation )
    @field_validator("project_id")
    def validate_project_id(cls, v):
        if not v.strip():
            raise ValueError("project_id must not be empty or whitespace")
        
        if not v.isalnum():
            raise ValueError("project_id must be alphanumeric")
        return v


    class Config:
        arbitrary_types_allowed = True
        # json_encoders = {
        #     ObjectId: str
        # }

    
    @classmethod
    def get_indexes(cls):

        return [
            {
                "key": [
                    ("project_id", 1)
                ],
                "name": "project_id_index_1",
                "unique": True
            }
        ]
    