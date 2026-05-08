from fastapi import FastAPI # type: ignore
from routes import base_router, data_router, nlp_router, conversation_router, vectors_router
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient # type: ignore
from helpers.config import get_settings
from helpers.collections import get_system_reserved_project_ids, build_collection_name
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templates import TemplateParser
# Set up logging
import logging
logger = logging.getLogger(__name__)
settings = get_settings()

# Set up Prometheus metrics
from utils import setup_metrics

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This handles startup and shutdown of resources. Code before `yield` runs at startup.
    Code after `yield` runs at shutdown.
    """

    # mongodb 
    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]
    logger.info("INFO:     MongoDB connection established")

    # vectordb 
    vectordb_provider_factory = VectorDBProviderFactory(settings)
    app.vectordb_client = vectordb_provider_factory.create(provider=settings.VECTOR_DB_BACKEND)
    app.vectordb_client.connect()
    logger.info(f"INFO:     VectorDB client for {settings.VECTOR_DB_BACKEND} initialized")

    async def validate_system_collections():
        for collection_id in get_system_reserved_project_ids():
            collection_name = build_collection_name(collection_id)
            if not app.vectordb_client.is_collection_existed(collection_name=collection_name):
                logger.warning(f"System collection not found: {collection_name}")

    await validate_system_collections()

    # Transformers' (clients) 
    llm_provider_factory = LLMProviderFactory(settings)
    # llm generation client
    app.generation_client = llm_provider_factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id = settings.GENERATION_MODEL_ID)
    logger.info(f"INFO:     LLM generation client for {settings.GENERATION_BACKEND} initialized")


    # llm embedding client
    app.embedding_client = llm_provider_factory.create(provider=settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID,
                                             embedding_size=settings.EMBEDDING_MODEL_SIZE)
    logger.info(f"INFO:     LLM embedding client for {settings.EMBEDDING_BACKEND} initialized")
    
    # template parser
    app.template_parser = TemplateParser(
        language=settings.PRIMARY_LANGUAGE,
        default_language=settings.DEFAULT_LANGUAGE,
    )

    yield # Application runs here

    app.mongo_conn.close()
    logger.info("INFO:     MongoDB connection closed")

    app.vectordb_client.disconnect()
    logger.info(f"INFO:     VectorDB client for {settings.VECTOR_DB_BACKEND} disconnected") 


app = FastAPI(lifespan= lifespan, title="Legal RAG Chatbot API")

setup_metrics(app) # Set up Prometheus metrics and endpoint

app.include_router(base_router)
app.include_router(data_router)
app.include_router(nlp_router)
app.include_router(conversation_router)
app.include_router(vectors_router)
