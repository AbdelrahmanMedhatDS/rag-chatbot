from fastapi import FastAPI
from routes import base_router, data_router 
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This handles startup and shutdown of resources like MongoDB.
    Code before `yield` runs at startup.
    Code after `yield` runs at shutdown.
    """

    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]
    print("INFO:     MongoDB connected")
    
    yield  

    app.mongo_conn.close()
    print("INFO:     MongoDB connection closed")



app = FastAPI(lifespan= lifespan, title="Legal RAG Chatbot API")

app.include_router(base_router)
app.include_router(data_router)