from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database.database import get_supabase

router = APIRouter(prefix="/api/names", tags=["names"])


class NameCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class NameOut(BaseModel):
    name: str


@router.post("", response_model=NameOut, status_code=201)
def create_name(payload: NameCreate) -> NameOut:
    """Store a submitted name in Supabase."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty")

    try:
        get_supabase().table("names").insert({"name": name}).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to store name: {exc}"
        ) from exc

    return NameOut(name=name)


@router.get("", response_model=list[NameOut])
def list_names() -> list[NameOut]:
    """Return all stored names."""
    try:
        result = get_supabase().table("names").select("name").execute()
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to load names: {exc}"
        ) from exc

    rows = result.data or []
    return [NameOut(name=row["name"]) for row in rows]