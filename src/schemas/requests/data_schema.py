from pydantic import BaseModel
from typing import Optional

class ProcessRequest(BaseModel): # new schema for process endpoint request body using Pydantic validation
    file_id: str = None # make it optionally default is none
    chunk_size: Optional[int] = 100
    overlap_size: Optional[int] = 20
    do_reset: Optional[int] = 0