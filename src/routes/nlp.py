from fastapi import FastAPI, APIRouter, status, Request
from fastapi.responses import JSONResponse
from schemas import PushRequest, SearchRequest, RetrievedDocumentSchema
from models import ProjectModel
from models import ChunkModel
from models import ConversationModel
from controllers import NLPController
from enums import ResponseSignal
from helpers.collections import is_reserved_project_id, allow_reserved_writes, get_system_reserved_project_ids

import logging
import asyncio
import uuid

logger = logging.getLogger('uvicorn.error')

nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"],
)

@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: str, push_request: PushRequest):

    if is_reserved_project_id(project_id):
        if allow_reserved_writes():
            logger.warning(f"Reserved project_id write allowed on index push: {project_id}")
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.PROJECT_ID_RESERVED.value,
                    "details": {
                        "message": "project_id is reserved for system collections",
                        "reserved_project_ids": get_system_reserved_project_ids()
                    }
                }
            )

    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )

    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_from_db_or_insert_one(
        project_id=project_id
    )

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value
            }
        )
    
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser
    )

    has_records = True
    page_no = 1
    inserted_items_count = 0
    first_iteration = True  # Track first iteration for do_reset
    index_only_new = bool(push_request.index_only_new) and not bool(push_request.do_reset)

    while has_records:
        if index_only_new:
            # Atomic fetch-and-lock: no page_no needed because each call
            # locks the returned chunks, shrinking the unindexed pool.
            # Stale locks (from crashed runs) auto-expire after 10 min.
            page_chunks = await chunk_model.get_and_lock_unindexed_chunks(
                project_id=project.id
            )
        else:
            # Full re-index: use normal pagination with skip
            page_chunks = await chunk_model.get_poject_chunks(
                project_id=project.id,
                page_no=page_no,
                only_unindexed=False
            )
        
        if not page_chunks or len(page_chunks) == 0:
            has_records = False
            break

        chunk_object_ids = [chunk.id for chunk in page_chunks if chunk.id]
        chunks_ids = [
            str(uuid.uuid5(uuid.NAMESPACE_OID, str(chunk_id)))
            for chunk_id in chunk_object_ids
        ]
        
        # Only apply do_reset on the first iteration to avoid deleting previously inserted vectors
        should_reset = push_request.do_reset and first_iteration
        
        is_inserted = nlp_controller.index_into_vector_db(
            project=project,
            chunks=page_chunks,
            do_reset=should_reset,
            chunks_ids=chunks_ids
        )
        
        first_iteration = False  # Set to False after first iteration

        if not is_inserted:
            # Rollback: clear both indexed flag AND processing lock
            await chunk_model.mark_chunks_unindexed(chunk_ids=chunk_object_ids)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value
                }
            )
        
        # Mark chunks as indexed AFTER successful vector DB insertion
        # (for index_only_new this also clears the processing lock)
        await chunk_model.mark_chunks_indexed(chunk_ids=chunk_object_ids)
        
        inserted_items_count += len(page_chunks)
        
        # Only increment page_no for full re-index (stable dataset with skip).
        # For index_only_new, the pool shrinks naturally — no skip needed.
        if not index_only_new:
            page_no += 1
        
    return JSONResponse(
        content={
            "signal": ResponseSignal.INSERT_INTO_VECTORDB_SUCCESS.value,
            "inserted_items_count": inserted_items_count
        }
    )

@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: str):
    
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_from_db_or_insert_one(
        project_id=project_id
    )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser
    )

    collection_info = nlp_controller.get_vector_db_collection_info(project=project)

    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_COLLECTION_RETRIEVED.value,
            "collection_info": collection_info
        }
    )

@nlp_router.post("/index/search/{project_id}")
async def search_index(request: Request, project_id: str, search_request: SearchRequest):
    
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_from_db_or_insert_one(
        project_id=project_id
    )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser
    )

    results :RetrievedDocumentSchema = await nlp_controller.search_vector_db_collection(
        project=project, text=search_request.text, limit=search_request.limit
    )

    if not results:
        return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.VECTORDB_SEARCH_ERROR.value
                }
            )
    
    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_SEARCH_SUCCESS.value,
            "results": [ result.dict()  for result in results ]
        }
    )


@nlp_router.post("/index/answer/{project_id}")
async def search_index(request: Request, project_id: str, search_request: SearchRequest):
    
    try:
        project_model = await ProjectModel.create_instance(
            db_client=request.app.db_client
        )

        project = await project_model.get_project_from_db_or_insert_one(
            project_id=project_id
        )

        nlp_controller = NLPController(
            vectordb_client=request.app.vectordb_client,
            generation_client=request.app.generation_client,
            embedding_client=request.app.embedding_client,
            template_parser=request.app.template_parser
        )

        conversation_model = None
        if search_request.use_memory and search_request.user_id and search_request.conversation_id:
            conversation_model = await ConversationModel.create_instance(
                db_client=request.app.db_client
            )

        answer, full_prompt, chat_history, conversation = await nlp_controller.answer_rag_question(
            project=project,
            query= search_request.text,
            limit= search_request.limit,
            chat_history=search_request.chat_history,
            conversation_model=conversation_model,
            conversation_id=search_request.conversation_id,
            user_id=search_request.user_id,
            use_memory=search_request.use_memory,
            enable_query_rewrite=search_request.enable_query_rewrite
        )

        if not answer:
            return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "signal": ResponseSignal.RAG_ANSWER_ERROR.value
                    }
                )

        if conversation_model and conversation:
            if conversation.title is None or str(conversation.title).strip() == "":

                async def _generate_title():
                    try:
                        title = nlp_controller.conversation_controller.generate_conversation_title(query=search_request.text)
                        if title:
                            await conversation_model.set_title_if_missing(
                                project_id=project_id,
                                user_id=search_request.user_id,
                                conversation_id=conversation.conversation_id,
                                title=title
                            )
                    except Exception as e:
                        logger.error(f"Title generation failed: {e}", exc_info=True)

                asyncio.create_task(_generate_title())

        response_payload = {
            "signal": ResponseSignal.RAG_ANSWER_SUCCESS.value,
            "answer": answer,
            "full_prompt": full_prompt,
            "chat_history": chat_history,
        }

        if conversation:
            response_payload["conversation_id"] = conversation.conversation_id
            response_payload["conversation_title"] = conversation.title

        return JSONResponse(content=response_payload)

    except Exception as e:
        logger.error(f"answer_rag_question endpoint failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "signal": ResponseSignal.RAG_ANSWER_ERROR.value,
                "error": str(e),
            }
        )
