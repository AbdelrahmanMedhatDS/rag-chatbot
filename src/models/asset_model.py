from .base_data_model import BaseDataModel
from schemas import AssetSchema
from enums import DataBaseEnum
from bson import ObjectId

class AssetModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_collection = self.db_client[DataBaseEnum.DB_COLLECTION_ASSET_NAME.value]

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        await instance.init_collection()
        return instance

    async def init_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.DB_COLLECTION_ASSET_NAME.value not in all_collections:
            self.db_collection = self.db_client[DataBaseEnum.DB_COLLECTION_ASSET_NAME.value]
            indexes = AssetSchema.get_indexes()
            for index in indexes:
                await self.db_collection.create_index(
                    index["key"],
                    name=index["name"],
                    unique=index["unique"]
                )

    async def insert_asset_in_db(self, asset: AssetSchema):

        result = await self.db_collection.insert_one(asset.model_dump(by_alias=True, exclude_unset=True))
        asset.id = result.inserted_id
 
        return asset

    async def get_all_project_assets_from_db(self, asset_project_id: str, asset_type: str):

        records = await self.db_collection.find({ # filters
            "asset_project_id": ObjectId(asset_project_id) if isinstance(asset_project_id, str) else asset_project_id,
            "asset_type": asset_type,
        }).to_list(length=None)

        return [
            AssetSchema(**record)
            for record in records
        ]

    async def get_asset_record_from_db(self, asset_project_id: str, asset_name: str):

        record = await self.db_collection.find_one({
            "asset_project_id": ObjectId(asset_project_id) if isinstance(asset_project_id, str) else asset_project_id,
            "asset_name": asset_name,
        })

        if record:
            return AssetSchema(**record)
        
        return None


    