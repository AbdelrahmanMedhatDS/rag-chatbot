from enum import Enum

class ResponseSignal(Enum):

    FILE_VALIDATED_SUCCESS = "file_validate_successfully"
    FILE_TYPE_NOT_SUPPORTED = "file_type_not_supported"
    FILE_SIZE_EXCEEDED = "file_size_exceeded"
    FILE_UPLOAD_SUCCESS = "file_upload_success"
    FILE_UPLOAD_FAILED = "file_upload_failed"
    
    PROCESSING_FAILED =     "processing_failed"
    PROCESSING_STARTED =    "processing_started"   
    PROCESSING_COMPLETED =  "processing_completed"
    PROCESSING_RESET =      "processing_reset"

    NO_FILES_ERROR = "not_found_files"
    FILE_ID_ERROR = "no_file_found_with_this_id"
    PROJECT_NOT_FOUND_ERROR = "project_not_found"
    INSERT_INTO_VECTORDB_ERROR = "insert_into_vectordb_error"
    INSERT_INTO_VECTORDB_SUCCESS = "inserted_into_vectordb_successfully"
    GENERATE_RESPONSE_ERROR = "generate_response_error"
    GENERATE_RESPONSE_SUCCESS = "generate_response_successfully"
    SEARCH_VECTORDB_ERROR = "search_vectordb_error"
    SEARCH_VECTORDB_SUCCESS = "search_vectordb_successfully"
    TEMPLATE_PARSING_ERROR = "template_parsing_error"
    TEMPLATE_PARSING_SUCCESS = "template_parsing_successfully"
    CHUNKING_ERROR = "chunking_error"
    CHUNKING_SUCCESS = "chunking_successfully"
    EMBEDDING_ERROR = "embedding_error"
    VECTORDB_COLLECTION_RETRIEVED = "vectordb_collection_retrieved_successfully"
    VECTORDB_SEARCH_ERROR = "vectordb_search_error"
    VECTORDB_SEARCH_SUCCESS = "vectordb_search_successfully"
    RAG_ANSWER_ERROR = "rag_answer_error"
    RAG_ANSWER_SUCCESS = "rag_answer_successfully"
    