import os
from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from controllers import ProcessController
from helpers import get_settings, Settings
from controllers import DataController, ProjectController
from enums import ResponseSignal
import aiofiles # async file handling lib
import logging
logger = logging.getLogger("UVicorn.errors")
from schemas import ProcessRequest

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1" , "data"],
)

@data_router.post("/upload/{project_id}")
async def upload_data(project_id:str, file:UploadFile, 
                      app_settings:Settings=Depends(get_settings)):
    
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
        
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
                "file_id": file_id
            }
        )

@data_router.post("/process/{project_id}")
async def process_endpoint(project_id:str, process_request:ProcessRequest):
    file_id=process_request.file_id
    chunk_size=process_request.chunk_size
    overlap_size=process_request.overlap_size
    do_reset=process_request.do_reset

    process_controller = ProcessController(project_id=project_id,file_id=file_id)

    file_content = process_controller.get_file_content()

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

    return file_chunks