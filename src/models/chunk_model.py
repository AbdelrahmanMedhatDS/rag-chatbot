from .base_data_model import BaseDataModel
from schemas import ChunkSchema
from enums import DataBaseEnum
from bson.objectid import ObjectId
from pymongo import InsertOne
from datetime import datetime, timedelta
from typing import List

class ChunkModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_collection = self.db_client[DataBaseEnum.DB_COLLECTION_CHUNK_NAME.value]


    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        await instance.init_collection()
        return instance

    async def init_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.DB_COLLECTION_CHUNK_NAME.value not in all_collections:
            self.db_collection = self.db_client[DataBaseEnum.DB_COLLECTION_CHUNK_NAME.value]
        indexes = ChunkSchema.get_indexes()
        for index in indexes:
            await self.db_collection.create_index(
                index["key"],
                name=index["name"],
                unique=index["unique"]
            )




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
    

    async def get_poject_chunks(self, project_id: ObjectId, page_no: int=1, page_size: int=50,
                                only_unindexed: bool = False):
        query = {
            "chunk_project_id": project_id
        }

        if only_unindexed:
            query = {
                "$and": [
                    {"chunk_project_id": project_id},
                    {
                        "$or": [
                            {"chunk_is_indexed": False},
                            {"chunk_is_indexed": {"$exists": False}}
                        ]
                    }
                ]
            }

        records = await self.db_collection.find(query).sort(
                    "_id", 1
                ).skip(
                    (page_no-1) * page_size
                ).limit(page_size).to_list(length=None)

        return [
            ChunkSchema(**record)
            for record in records
        ]
    
    async def get_and_lock_unindexed_chunks(self, project_id: ObjectId, page_size: int=50,
                                             lock_timeout_minutes: int=10):
        """
        Atomically fetch unindexed chunks and mark them as being processed.
        This prevents race conditions when multiple processes try to index simultaneously.

        Uses a separate 'chunk_is_processing' lock with a timeout so that if the
        server crashes mid-push, stale locks auto-expire and those chunks become
        available again on the next push.

        NOTE: No skip/page_no is used because each call locks (removes from pool)
        the returned chunks. Always fetches from the top of the unindexed set.
        """
        stale_cutoff = datetime.utcnow() - timedelta(minutes=lock_timeout_minutes)

        # Find chunks that are NOT indexed AND (not processing OR stale processing lock)
        query = {
            "$and": [
                {"chunk_project_id": project_id},
                {
                    "$or": [
                        {"chunk_is_indexed": False},
                        {"chunk_is_indexed": {"$exists": False}}
                    ]
                },
                {
                    "$or": [
                        {"chunk_is_processing": False},
                        {"chunk_is_processing": {"$exists": False}},
                        {"chunk_processing_at": {"$lt": stale_cutoff}}  # stale lock expired
                    ]
                }
            ]
        }

        # Get chunk IDs (no skip — pool shrinks as we lock)
        cursor = self.db_collection.find(query, {"_id": 1}).sort(
            "_id", 1
        ).limit(page_size)

        chunk_ids = [doc["_id"] async for doc in cursor]

        if not chunk_ids:
            return []

        now = datetime.utcnow()

        # Atomically set the processing lock (NOT chunk_is_indexed)
        result = await self.db_collection.update_many(
            {
                "_id": {"$in": chunk_ids},
                "$or": [
                    {"chunk_is_processing": False},
                    {"chunk_is_processing": {"$exists": False}},
                    {"chunk_processing_at": {"$lt": stale_cutoff}}
                ]
            },
            {"$set": {"chunk_is_processing": True, "chunk_processing_at": now}}
        )

        if result.modified_count > 0:
            # Fetch full data only for the chunks we actually locked
            locked_chunks = await self.db_collection.find(
                {"_id": {"$in": chunk_ids}, "chunk_is_processing": True, "chunk_processing_at": now}
            ).to_list(length=None)

            return [ChunkSchema(**record) for record in locked_chunks]

        return []

    async def mark_chunks_indexed(self, chunk_ids: List[ObjectId]):
        if not chunk_ids:
            return 0

        normalized_ids = [
            ObjectId(cid) if isinstance(cid, str) else cid
            for cid in chunk_ids
        ]

        result = await self.db_collection.update_many(
            {"_id": {"$in": normalized_ids}},
            {
                "$set": {
                    "chunk_is_indexed": True,
                    "chunk_indexed_at": datetime.utcnow(),
                    "chunk_is_processing": False
                },
                "$unset": {"chunk_processing_at": ""}
            }
        )

        return result.modified_count
    
    async def mark_chunks_unindexed(self, chunk_ids: List[ObjectId]):
        """Rollback method: clears both indexed flag AND processing lock"""
        if not chunk_ids:
            return 0

        normalized_ids = [
            ObjectId(cid) if isinstance(cid, str) else cid
            for cid in chunk_ids
        ]

        result = await self.db_collection.update_many(
            {"_id": {"$in": normalized_ids}},
            {
                "$set": {"chunk_is_indexed": False, "chunk_is_processing": False},
                "$unset": {"chunk_indexed_at": "", "chunk_processing_at": ""}
            }
        )

        return result.modified_count
    

    