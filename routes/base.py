from fastapi import FastAPI, APIRouter

base_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1"],
)

# the default route for health checking;
@base_router.get("/")
def read_root():
    return{
        "messege":"server is running"
    }