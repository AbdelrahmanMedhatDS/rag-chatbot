from typing import List
from .config import get_settings


def get_collection_prefix() -> str:
    settings = get_settings()
    if settings.VECTOR_DB_COLLECTION_PREFIX:
        return settings.VECTOR_DB_COLLECTION_PREFIX
    return "collection_"


def build_collection_name(project_id: str) -> str:
    prefix = get_collection_prefix()
    return f"{prefix}{str(project_id).strip()}".strip()


def get_system_reserved_project_ids() -> List[str]:
    settings = get_settings()
    return [str(pid).strip() for pid in settings.SYSTEM_RESERVED_PROJECT_IDS if str(pid).strip()]


def get_system_collection_names() -> List[str]:
    return [build_collection_name(pid) for pid in get_system_reserved_project_ids()]


def is_reserved_project_id(project_id: str) -> bool:
    project_id_str = str(project_id).strip()
    return project_id_str in set(get_system_reserved_project_ids())


def allow_reserved_writes() -> bool:
    settings = get_settings()
    return bool(settings.SYSTEM_ALLOW_RESERVED_WRITES)
