import os
from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from helpers import get_settings, Settings
from controllers import DataController, ProjectController
from models import ResponseSignal
import aiofiles # async file handling lib
data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1" , "data"],
)

@data_router.post("/upload/{project_id}")
async def upload_data(project_id:str, file:UploadFile, 
                      app_settings:Settings=Depends(get_settings)):
    
    # validate file properties
    is_valid, result_signal = DataController().validate_uploaded_file(file=file)

    if not is_valid:
            
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": result_signal
            }
        )
    
    # handle file storage step1:
    project_dir_path  = ProjectController().get_project_path(project_id=project_id)
    file_path = os.path.join(
        project_dir_path,
        file.filename
    )
    
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(512000) :
            await f.write(chunk)

    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value
            }
        )
