import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from database.repository import Repository
from deps import get_repo
from schemas import CountrySummary, MentionOut
from services.map_data import mentions_for_country, summarize_countries

router = APIRouter(prefix="/api/collections", tags=["map"])


def _require_collection(repo: Repository, collection_id: UUID) -> None:
    if repo.get_collection(str(collection_id)) is None:
        raise HTTPException(status_code=404, detail="Collection not found")


@router.get("/{collection_id}/map/countries", response_model=list[CountrySummary])
def countries(collection_id: UUID, repo: Repository = Depends(get_repo)):
    """Countries that have at least one place mentioned in this collection."""
    _require_collection(repo, collection_id)
    return summarize_countries(repo.list_mention_details(str(collection_id)))


@router.get("/{collection_id}/map/countries/{country_code}/mentions",
            response_model=list[MentionOut])
def country_mentions(collection_id: UUID, country_code: str,
                     repo: Repository = Depends(get_repo)):
    """Every mention in one country, each with the page it came from."""
    if not re.fullmatch(r"[A-Za-z]{2}", country_code):
        raise HTTPException(status_code=422, detail="country_code must be 2 letters, e.g. CH")
    _require_collection(repo, collection_id)
    return mentions_for_country(repo.list_mention_details(str(collection_id)), country_code)