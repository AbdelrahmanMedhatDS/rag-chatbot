from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse
from schemas import ConversationCreateRequest, ConversationListRequest
from models import ConversationModel
from controllers import BaseController
from enums import ResponseSignal

conversation_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "conversations"],
)


def _serialize_message(message):
    return {
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def _serialize_conversation(conversation, include_messages: bool = False):
    payload = {
        "conversation_id": conversation.conversation_id,
        "user_id": conversation.user_id,
        "project_id": conversation.project_id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
        "message_count": len(conversation.messages) if conversation.messages else 0,
    }

    if include_messages:
        payload["messages"] = [
            _serialize_message(message)
            for message in (conversation.messages or [])
        ]

    return payload


@conversation_router.post("/conversations/{project_id}")
async def create_conversation(request: Request, project_id: str, create_request: ConversationCreateRequest):

    if not create_request.user_id or not str(create_request.user_id).strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.CONVERSATION_CREATE_ERROR.value,
                "details": {
                    "message": "user_id is required"
                }
            }
        )

    conversation_id = create_request.conversation_id
    if not conversation_id or not str(conversation_id).strip():
        conversation_id = BaseController().generate_random_string()

    conversation_model = await ConversationModel.create_instance(
        db_client=request.app.db_client
    )

    conversation = await conversation_model.create_conversation(
        project_id=project_id,
        user_id=create_request.user_id,
        conversation_id=conversation_id
    )

    if not conversation:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.CONVERSATION_CREATE_ERROR.value,
            }
        )

    return JSONResponse(
        content={
            "signal": ResponseSignal.CONVERSATION_CREATED_SUCCESS.value,
            "conversation": _serialize_conversation(conversation)
        }
    )


@conversation_router.post("/conversations/{project_id}/list")
async def list_conversations(request: Request, project_id: str, list_request: ConversationListRequest):

    if not list_request.user_id or not str(list_request.user_id).strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.CONVERSATION_LIST_ERROR.value,
                "details": {
                    "message": "user_id is required"
                }
            }
        )

    page = list_request.page if list_request.page and list_request.page >= 1 else 1
    page_size = list_request.page_size if list_request.page_size and list_request.page_size >= 1 else 20

    conversation_model = await ConversationModel.create_instance(
        db_client=request.app.db_client
    )

    conversations = await conversation_model.list_conversations(
        project_id=project_id,
        user_id=list_request.user_id,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        content={
            "signal": ResponseSignal.CONVERSATION_LIST_RETRIEVED_SUCCESS.value,
            "page": page,
            "page_size": page_size,
            "count": len(conversations),
            "conversations": [
                _serialize_conversation(conversation)
                for conversation in conversations
            ]
        }
    )


@conversation_router.get("/conversations/{project_id}/{conversation_id}")
async def get_conversation(request: Request, project_id: str, conversation_id: str, user_id: str):

    if not user_id or not str(user_id).strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.CONVERSATION_NOT_FOUND_ERROR.value,
                "details": {
                    "message": "user_id is required"
                }
            }
        )

    conversation_model = await ConversationModel.create_instance(
        db_client=request.app.db_client
    )

    conversation = await conversation_model.get_conversation(
        project_id=project_id,
        user_id=user_id,
        conversation_id=conversation_id
    )

    if not conversation:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.CONVERSATION_NOT_FOUND_ERROR.value,
            }
        )

    return JSONResponse(
        content={
            "signal": ResponseSignal.CONVERSATION_RETRIEVED_SUCCESS.value,
            "conversation": _serialize_conversation(conversation, include_messages=True)
        }
    )


@conversation_router.delete("/conversations/{project_id}/{conversation_id}")
async def delete_conversation(request: Request, project_id: str, conversation_id: str, user_id: str):

    if not user_id or not str(user_id).strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.CONVERSATION_DELETE_ERROR.value,
                "details": {
                    "message": "user_id is required"
                }
            }
        )

    conversation_model = await ConversationModel.create_instance(
        db_client=request.app.db_client
    )

    deleted_count = await conversation_model.delete_conversation(
        project_id=project_id,
        user_id=user_id,
        conversation_id=conversation_id
    )

    if deleted_count == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.CONVERSATION_NOT_FOUND_ERROR.value,
            }
        )

    return JSONResponse(
        content={
            "signal": ResponseSignal.CONVERSATION_DELETED_SUCCESS.value,
            "deleted": True
        }
    )
