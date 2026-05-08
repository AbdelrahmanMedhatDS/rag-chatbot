from .base_data_model import BaseDataModel
from schemas import ConversationSchema, ChatMessageSchema
from enums import DataBaseEnum
from datetime import datetime
from typing import List
from pymongo import ReturnDocument


class ConversationModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_collection = self.db_client[DataBaseEnum.DB_COLLECTION_CONVERSATION_NAME.value]

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        await instance.init_collection()
        return instance

    async def init_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.DB_COLLECTION_CONVERSATION_NAME.value not in all_collections:
            self.db_collection = self.db_client[DataBaseEnum.DB_COLLECTION_CONVERSATION_NAME.value]
            indexes = ConversationSchema.get_indexes()
            for index in indexes:
                await self.db_collection.create_index(
                    index["key"],
                    name=index["name"],
                    unique=index["unique"]
                )

    async def get_conversation(self, project_id: str, user_id: str, conversation_id: str):
        record = await self.db_collection.find_one({
            "project_id": project_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
        })

        if record is None:
            return None

        return ConversationSchema(**record)

    async def create_conversation(self, project_id: str, user_id: str, conversation_id: str, title: str = None):
        existing = await self.get_conversation(project_id=project_id, user_id=user_id, conversation_id=conversation_id)
        if existing:
            return existing

        now = datetime.utcnow()
        conversation = ConversationSchema(
            project_id=project_id,
            user_id=user_id,
            conversation_id=conversation_id,
            title=title,
            created_at=now,
            updated_at=now,
            messages=[],
        )

        result = await self.db_collection.insert_one(conversation.model_dump(by_alias=True, exclude_unset=True))
        conversation.id = result.inserted_id
        return conversation

    async def list_conversations(self, project_id: str, user_id: str, page: int = 1, page_size: int = 20):
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        cursor = self.db_collection.find({
            "project_id": project_id,
            "user_id": user_id,
        }).sort("updated_at", -1).skip((page - 1) * page_size).limit(page_size)

        items = []
        async for record in cursor:
            items.append(ConversationSchema(**record))

        return items

    async def delete_conversation(self, project_id: str, user_id: str, conversation_id: str):
        result = await self.db_collection.delete_one({
            "project_id": project_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
        })

        return result.deleted_count

    async def append_messages(self, project_id: str, user_id: str, conversation_id: str,
                              messages: List[ChatMessageSchema]):
        if not messages:
            return await self.get_conversation(project_id=project_id, user_id=user_id, conversation_id=conversation_id)

        now = datetime.utcnow()
        message_payload = [
            message.model_dump(by_alias=True, exclude_unset=True)
            for message in messages
        ]

        record = await self.db_collection.find_one_and_update(
            {
                "project_id": project_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
            },
            {
                "$setOnInsert": {
                    "project_id": project_id,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "created_at": now,
                    "title": None,
                },
                "$set": {
                    "updated_at": now,
                },
                "$push": {
                    "messages": {
                        "$each": message_payload,
                    }
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

        if not record:
            return None

        return ConversationSchema(**record)

    async def set_title_if_missing(self, project_id: str, user_id: str, conversation_id: str, title: str):
        if not title:
            return False

        result = await self.db_collection.update_one(
            {
                "project_id": project_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "$or": [
                    {"title": {"$exists": False}},
                    {"title": None},
                    {"title": ""},
                ]
            },
            {
                "$set": {
                    "title": title,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        return result.modified_count > 0
