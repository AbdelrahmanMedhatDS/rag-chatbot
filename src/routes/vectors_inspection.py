from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from schemas import VectorInspectRequest, VectorDuplicatesRequest
from enums import ResponseSignal
import logging

logger = logging.getLogger("vectors_inspector")

vectors_router = APIRouter(
    prefix="/api/v1/vectors",
    tags=["api_v1", "vectors"],
)


def _clamp_limit(value: int, default: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default

    if parsed < 1:
        return default
    if parsed > max_value:
        return max_value
    return parsed


def _normalize_offset(offset_value):
    if offset_value is None:
        return None, 0

    if isinstance(offset_value, str):
        cleaned = offset_value.strip()
        if cleaned == "" or cleaned == "0":
            return None, 0
        if cleaned.isdigit():
            return int(cleaned), offset_value
        return cleaned, offset_value

    if isinstance(offset_value, int):
        if offset_value == 0:
            return None, 0
        return offset_value, offset_value

    return offset_value, offset_value


def _extract_vector(vector_data):
    if vector_data is None:
        return None
    if isinstance(vector_data, dict):
        if len(vector_data) == 0:
            return None
        return next(iter(vector_data.values()))
    return vector_data


def _get_vector_size(collection_info) -> int:
    if collection_info is None:
        return 0

    try:
        vectors_config = collection_info.config.params.vectors
    except Exception:
        return 0

    if hasattr(vectors_config, "size"):
        return int(vectors_config.size)

    if hasattr(vectors_config, "map"):
        values = list(vectors_config.map.values())
        if values and hasattr(values[0], "size"):
            return int(values[0].size)

    if isinstance(vectors_config, dict):
        if len(vectors_config) == 1:
            first_value = next(iter(vectors_config.values()))
            if hasattr(first_value, "size"):
                return int(first_value.size)
        return 0

    return 0


def _normalize_status(status_value):
    if status_value is None:
        return None
    if hasattr(status_value, "value"):
        return status_value.value
    return str(status_value)


def _resolve_count(value, fallback: int) -> int:
    if value is None:
        return fallback

    if isinstance(value, dict):
        total = 0
        for item in value.values():
            try:
                total += int(item)
            except (TypeError, ValueError):
                continue
        return total if total else fallback

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback

    return parsed if parsed else fallback


@vectors_router.post("/inspect/{collection_name}")
async def inspect_vectors(
    request: Request,
    collection_name: str,
    inspect_request: VectorInspectRequest,
):
    vectordb_client = request.app.vectordb_client

    if not vectordb_client.is_collection_existed(collection_name=collection_name):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.VECTORDB_COLLECTION_NOT_FOUND.value,
                "collection_name": collection_name,
            },
        )

    limit = _clamp_limit(inspect_request.limit, default=50, max_value=1000)
    include_vectors = bool(inspect_request.include_vectors)
    offset_value, offset_response = _normalize_offset(inspect_request.offset)

    collection_info = vectordb_client.get_collection_info(
        collection_name=collection_name
    )
    vector_size = _get_vector_size(collection_info)

    points, next_offset = vectordb_client.scroll_collection(
        collection_name=collection_name,
        limit=limit,
        offset=offset_value,
        with_payload=True,
        with_vectors=include_vectors,
    )

    vectors = []
    for point in points:
        payload = point.payload or {}
        text = payload.get("text")
        metadata = payload.get("metadata")
        text_length = len(text) if text else 0

        vector_data = _extract_vector(getattr(point, "vector", None))
        vector_length = len(vector_data) if vector_data else vector_size

        vector_item = {
            "id": str(point.id),
            "text": text,
            "text_length": text_length,
            "metadata": metadata,
            "vector_length": vector_length,
        }

        if include_vectors:
            vector_item["vector_sample"] = (
                vector_data[:10] if vector_data else []
            )

        vectors.append(vector_item)

    total_vectors = getattr(collection_info, "points_count", 0) or 0

    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_COLLECTION_INSPECT_SUCCESS.value,
            "collection_name": collection_name,
            "total_vectors": total_vectors,
            "returned_vectors": len(vectors),
            "offset": offset_response,
            "next_offset": str(next_offset) if next_offset is not None else None,
            "limit": limit,
            "vectors": vectors,
        }
    )


@vectors_router.post("/duplicates/{collection_name}")
async def detect_duplicate_vectors(
    request: Request,
    collection_name: str,
    duplicates_request: VectorDuplicatesRequest,
):
    vectordb_client = request.app.vectordb_client

    if not vectordb_client.is_collection_existed(collection_name=collection_name):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.VECTORDB_COLLECTION_NOT_FOUND.value,
                "collection_name": collection_name,
            },
        )

    limit = _clamp_limit(duplicates_request.limit, default=5000, max_value=50000)
    min_count = max(2, int(duplicates_request.min_count or 2))
    max_groups = max(1, int(duplicates_request.max_groups or 100))
    offset_value, offset_response = _normalize_offset(duplicates_request.offset)

    remaining = limit
    cursor = offset_value
    scanned = 0
    last_offset = None
    text_to_ids = {}

    while remaining > 0:
        page_limit = min(200, remaining)

        points, next_offset = vectordb_client.scroll_collection(
            collection_name=collection_name,
            limit=page_limit,
            offset=cursor,
            with_payload=True,
            with_vectors=False,
        )

        if not points:
            last_offset = next_offset
            break

        for point in points:
            payload = point.payload or {}
            text = payload.get("text")
            if not text:
                continue

            ids = text_to_ids.get(text)
            if ids is None:
                text_to_ids[text] = [str(point.id)]
            else:
                ids.append(str(point.id))

        scanned += len(points)
        remaining -= len(points)
        last_offset = next_offset

        if next_offset is None:
            break

        cursor = next_offset

    duplicates = [
        {"text": text, "count": len(ids), "ids": ids}
        for text, ids in text_to_ids.items()
        if len(ids) >= min_count
    ]
    duplicates.sort(key=lambda item: item["count"], reverse=True)
    if max_groups:
        duplicates = duplicates[:max_groups]

    collection_info = vectordb_client.get_collection_info(
        collection_name=collection_name
    )
    total_vectors = getattr(collection_info, "points_count", 0) or 0

    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_DUPLICATES_SUCCESS.value,
            "collection_name": collection_name,
            "total_vectors": total_vectors,
            "scanned_vectors": scanned,
            "returned_duplicates": len(duplicates),
            "offset": offset_response,
            "next_offset": str(last_offset) if last_offset is not None else None,
            "limit": limit,
            "min_count": min_count,
            "duplicates": duplicates,
        }
    )


@vectors_router.get("/collections")
async def list_vector_collections(request: Request):
    vectordb_client = request.app.vectordb_client

    try:
        collections_response = vectordb_client.list_all_collections()
    except Exception as exc:
        logger.error(f"Error listing collections: {exc}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.VECTORDB_COLLECTIONS_LIST_ERROR.value
            },
        )

    collections = getattr(collections_response, "collections", []) or []
    summaries = []

    for collection in collections:
        collection_name = getattr(collection, "name", None)
        if collection_name is None and isinstance(collection, dict):
            collection_name = collection.get("name")
        if not collection_name:
            continue

        info = vectordb_client.get_collection_info(
            collection_name=collection_name
        )

        points_count = getattr(info, "points_count", 0) or 0
        vectors_count = _resolve_count(
            getattr(info, "vectors_count", None),
            points_count,
        )
        indexed_vectors_count = _resolve_count(
            getattr(info, "indexed_vectors_count", None),
            points_count,
        )

        summaries.append(
            {
                "collection_name": collection_name,
                "status": _normalize_status(getattr(info, "status", None)),
                "points_count": points_count,
                "vectors_count": vectors_count,
                "indexed_vectors_count": indexed_vectors_count,
                "segments_count": getattr(info, "segments_count", 0) or 0,
                "vector_size": _get_vector_size(info),
            }
        )

    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_COLLECTIONS_LIST_SUCCESS.value,
            "count": len(summaries),
            "collections": summaries,
        }
    )
