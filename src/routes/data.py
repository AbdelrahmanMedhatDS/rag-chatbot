from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
from controllers import ProcessController
from helpers import get_settings, Settings
from controllers import DataController, ProjectController
from enums import ResponseSignal, AssetTypeEnum
import aiofiles # async file handling lib
import logging
import os
logger = logging.getLogger("UVicorn.errors")
from schemas import ProcessRequest
from models import ChunkModel, ProjectModel, AssetModel
from schemas import ChunkSchema, ProjectSchema, AssetSchema
from bson.objectid import ObjectId

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1" , "data"],
)

@data_router.post("/upload/{project_id}")
async def upload_data(request:Request, project_id:str, file:UploadFile, 
                      app_settings:Settings=Depends(get_settings)):
    
    db_client = request.app.db_client
    project_model = await ProjectModel.create_instance(db_client=db_client)

    project: ProjectSchema = await project_model.get_project_from_db_or_insert_one(project_id=project_id)

    # validate file properties
    data_controller = DataController()
    is_valid, result_signal = data_controller.validate_uploaded_file(file=file)

    if not is_valid:
            
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": result_signal
            }
        )
    
    # handle file storage step 1:
    file_path, file_id = data_controller.generate_unique_filepath(
        orig_file_name=file.filename,
        project_id=project_id
    )
    
    # handle file storage step 2:
    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(app_settings.MAX_CHUNK_SIZE) :
                await f.write(chunk)

    except Exception as e:
        # logging the error message for me 
        logger.error(f"error while uploading: {e}")
        
        # return only failed signal for user
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.FILE_UPLOAD_FAILED.value
            }
        )

    asset_model = await AssetModel.create_instance(
        db_client=db_client
    )

    asset_resource:AssetSchema = AssetSchema(
        asset_project_id = project.id,
        asset_type = AssetTypeEnum.FILE.value,
        asset_name = file_id,
        asset_size = os.path.getsize(file_path)
    )
    
    asset_resource = await asset_model.insert_asset_in_db(asset_resource)


    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
                "file_id": file_id,
                "asset's refrence": str(asset_resource.asset_name)
            }
        )

@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id:str, process_request:ProcessRequest):
    
    file_id=process_request.file_id
    chunk_size=process_request.chunk_size
    overlap_size=process_request.overlap_size
    do_reset=process_request.do_reset

    db_client = request.app.db_client
    
    project_model = await ProjectModel.create_instance(
        db_client=db_client
    )
    
    project: ProjectSchema = await project_model.get_project_from_db_or_insert_one(
        project_id=project_id
    )

    asset_model = await AssetModel.create_instance(
        db_client=db_client
    )
    
    project_files_ids = {}
    
    if file_id:
        asset_record = await asset_model.get_asset_record_from_db(
            asset_project_id=project.id,
            asset_name=file_id
        )

        if asset_record is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.FILE_ID_ERROR.value,
                }
            )
        
        project_files_ids = {
            asset_record.id: asset_record.asset_name
        }
    
        
    else:
    

        project_files = await asset_model.get_all_project_assets_from_db(
            asset_project_id=project.id,
            asset_type=AssetTypeEnum.FILE.value,
        )

        project_files_ids = {
            record.id: record.asset_name
            for record in project_files
        }


    if len(project_files_ids) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.NO_FILES_ERROR.value,
            }
        )
    
    process_controller = ProcessController(project_id=project_id)

    number_of_inserted_records = 0
    number_of_processed_files = 0

    
    chunk_model = await ChunkModel.create_instance(
    db_client=db_client
    )

    if do_reset == 1:
            _ = await chunk_model.delete_chunks_from_db_by_project_id(
                project_id=project.id
            )
    
    for asset_id, file_id in project_files_ids.items():
        
        file_content = process_controller.get_file_content(file_id=file_id)
        if file_content is None:
            logger.error(f"Failed to load content for file_id: {file_id}")
            continue
        
        file_chunks = process_controller.process_file_content(
            docs=file_content, 
            chunk_size=chunk_size,
            overlap_size=overlap_size
        )

        if file_chunks is None or len(file_chunks) == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.PROCESSING_FAILED.value
                }
            )
        
        file_chunks_records = [ # to make a list of valid pydantic (obj) chunks for the file
            ChunkSchema(
                chunk_text=chunk.page_content,
                chunk_metadata=chunk.metadata,
                chunk_order=idx+1,
                chunk_project_id=project.id,
                chunk_asset_id=asset_id
            )
            for idx, chunk in enumerate(file_chunks)
        ]

        number_of_inserted_records += await chunk_model.insert_many_chunks_in_db(chunks=file_chunks_records)
        number_of_processed_files += 1
    
    # return file_chunks # to see the chunks for single file_processed in postman
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "signal": ResponseSignal.PROCESSING_COMPLETED.value,
            "inserted_chunks": number_of_inserted_records,
            "processed_files": number_of_processed_files
        }
    )
