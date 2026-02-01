from fastapi import FastAPI
from routes import base_router, data_router 
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings
from stores.llm import LLMProviderFactory
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

    llm_provider_factory = LLMProviderFactory(settings)

    # generation client
    app.generation_client = llm_provider_factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id = settings.GENERATION_MODEL_ID)

    # embedding client
    app.embedding_client = llm_provider_factory.create(provider=settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID,
                                             embedding_size=settings.EMBEDDING_MODEL_SIZE)
    
    yield  

    app.mongo_conn.close()
    print("INFO:     MongoDB connection closed")



app = FastAPI(lifespan= lifespan, title="Legal RAG Chatbot API")

app.include_router(base_router)
app.include_router(data_router)