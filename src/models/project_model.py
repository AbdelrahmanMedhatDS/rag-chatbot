from .base_data_model import BaseDataModel
from schemas import ProjectSchema
from enums import DataBaseEnum

class ProjectModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_collection = self.db_client[DataBaseEnum.DB_COLLECTION_PROJECT_NAME.value]



    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        await instance.init_collection()
        return instance

    async def init_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.DB_COLLECTION_PROJECT_NAME.value not in all_collections:
            self.db_collection = self.db_client[DataBaseEnum.DB_COLLECTION_PROJECT_NAME.value]
            indexes = ProjectSchema.get_indexes()
            for index in indexes:
                await self.db_collection.create_index(
                    index["key"],
                    name=index["name"],
                    unique=index["unique"]
                )




    # create
    async def insert_project_in_db(self, project: ProjectSchema)-> ProjectSchema:

        result = await self.db_collection.insert_one(project.model_dump(by_alias=True, exclude_unset=True))
        project.id = result.inserted_id

        return project

    # read
    async def get_project_from_db_or_insert_one(self, project_id: str)-> ProjectSchema:

        record = await self.db_collection.find_one({ # filter
            "project_id": project_id 
        })

        if record is None:
            # create new project
            project = ProjectSchema(project_id=project_id)
            project = await self.insert_project_in_db(project=project)

            return project
        
        return ProjectSchema(**record)

    async def get_all_projects_from_db(self, page: int=1, page_size: int=10): # pagination

        # count total number of documents
        total_documents = await self.db_collection.count_documents({})

        # calculate total number of pages
        total_pages = total_documents // page_size
        if total_documents % page_size > 0:
            total_pages += 1

        cursor = self.db_collection.find({}).skip( (page-1) * page_size ).limit(page_size) # return MotorCursor
        projects = []
        async for document in cursor:
            projects.append(
                ProjectSchema(**document)
            )

        return projects, total_pages