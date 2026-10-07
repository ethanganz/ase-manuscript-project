from database.repository import Repository, SupabaseRepository
from services.storage import ObjectStorage, SupabaseStorage


def get_repo() -> Repository:
    """FastAPI dependency. Tests override this with an in-memory repository."""
    return SupabaseRepository()


def get_storage() -> ObjectStorage:
    """FastAPI dependency. Tests override this with in-memory storage."""
    return SupabaseStorage()