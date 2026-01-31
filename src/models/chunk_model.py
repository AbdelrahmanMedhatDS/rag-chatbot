from .base_data_model import BaseDataModel
from schemas import ChunkSchema
from enums import DataBaseEnum
from bson.objectid import ObjectId
from pymongo import InsertOne

class ChunkModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_collection = self.db_client[DataBaseEnum.DB_COLLECTION_CHUNK_NAME.value]

    async def insert_chunk_in_db(self, chunk: ChunkSchema):
        result = await self.db_collection.insert_one(chunk.model_dump(by_alias=True, exclude_unset=True))
        chunk.id = result.inserted_id
        return chunk

    async def get_chunk_from_db(self, chunk_id: str):
        result = await self.db_collection.find_one({
            "_id": ObjectId(chunk_id)
        })

        if result is None:
            return None
        
        return ChunkSchema(**result)

    async def insert_many_chunks_in_db(self, chunks: list, batch_size: int=100):

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]

            operations = [ # ready for bulk_write
                InsertOne(chunk.model_dump(by_alias=True, exclude_unset=True))
                for chunk in batch
            ]

            await self.db_collection.bulk_write(operations) 
        
        return len(chunks)

    async def delete_chunks_from_db_by_project_id(self, project_id: ObjectId):
        result = await self.db_collection.delete_many({
            "chunk_project_id": project_id
        })

        return result.deleted_count
    
    

    