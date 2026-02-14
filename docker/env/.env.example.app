# application
APP_NAME="legal-rag-chatbot"
APP_VERSION="0.1"

# -------------------------------------------------------------

# file
FILE_VALIDE_TYPES=["text/plain","application/pdf"]
FILE_MAX_SIZE=10 # 10MB
MAX_CHUNK_SIZE=512000 # 512KB


# -------------------------------------------------------------

# database 
MONGODB_URL= "mongodb://mongodb:27017/" 
MONGODB_DATABASE= "legal-rag-chatbot" 


# -------------------------------------------------------------

# llm  
GENERATION_BACKEND="OPENAI"
# GENERATION_BACKEND="COHERE"

EMBEDDING_BACKEND="COHERE"

OPENAI_API_KEY="openai_api_key_here"
OPENAI_API_URL=""

COHERE_API_KEY=""

GENERATION_MODEL_ID="gemma2:9b-instruct-q5_0"
# GENERATION_MODEL_ID="command-r7b-12-2024"

EMBEDDING_MODEL_ID="embed-multilingual-light-v3.0"
EMBEDDING_MODEL_SIZE=384

INPUT_DAFAULT_MAX_CHARACTERS=20000
GENERATION_DAFAULT_MAX_TOKENS=200
GENERATION_DAFAULT_TEMPERATURE=0.5


# -------------------------------------------------------------

# vector db
VECTOR_DB_BACKEND="QDRANT"
VECTOR_DB_PATH="qdrant_db"
VECTOR_DB_DISTANCE_METHOD="cosine"


# -------------------------------------------------------------

# default system propmt language
PRIMARY_LANGUAGE="en"
DEFAULT_LANGUAGE="en"