from fastapi import FastAPI, APIRouter
import os 
base_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1"],
)

# the default route for health checking;
@base_router.get("/")
def read_root():
    app_version = os.getenv("APP_VERSION")
    app_name = os.getenv("APP_NAME")
    return{
        "app name": app_name,
        "app version": app_version,
    }