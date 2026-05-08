from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from controllers.base_controller import BaseController
from helpers import get_settings, Settings
base_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1"],
)

# the default route for health checking;
@base_router.get("/")
async def read_root(request:Request, app_settings: Settings =Depends(get_settings)):
    # app_settings = get_settings()
    
    is_healthy = True
    
    base_controller = BaseController()
    if base_controller.get_database_path(app_settings.VECTOR_DB_PATH):
        vectore_db_path_check = "Qdrant vector database connection successful"
    else:
        vectore_db_path_check = "Qdrant vector database connection failed"
        is_healthy = False

    
    mongo_db_health_check = ""
    mongo_db_healthy = False
    try:
        if request.app.db_client is None:
            mongo_db_health_check = "MongoDB connection failed: Client is None"
        else:
            # Run command directly on the database object
            await request.app.db_client.command('ping')
            mongo_db_health_check = "MongoDB connection successful"
            mongo_db_healthy = True
            
    except Exception as e:
        mongo_db_health_check = f"MongoDB connection failed: {str(e)}"

    if not mongo_db_healthy:
        is_healthy = False

    app_version = app_settings.APP_VERSION
    app_name = app_settings.APP_NAME
    
    response_data = {
        "app name": app_name,
        "app version": app_version,
        "application status": "healthy" if is_healthy else "unhealthy",

        "transformer model in embedding backend": app_settings.EMBEDDING_BACKEND,
        "transformer model in generation backend": app_settings.GENERATION_BACKEND,
        
        "mongo_db_health_check": mongo_db_health_check,
        "vector_db_health_check_dir": vectore_db_path_check,
    }
    
    # Return 503 Service Unavailable if any dependency is unhealthy
    status_code = 200 if is_healthy else 503
    return JSONResponse(content=response_data, status_code=status_code)