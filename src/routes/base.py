from fastapi import APIRouter, Depends
from helpers import get_settings, Settings
base_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1"],
)

# the default route for health checking;
@base_router.get("/")
async def read_root(app_settings: Settings =Depends(get_settings)):
    # app_settings = get_settings()
    app_version = app_settings.APP_VERSION
    app_name = app_settings.APP_NAME
    return{
        "app name": app_name,
        "app version": app_version,
    }