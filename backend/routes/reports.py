"""Reporting collections, and the owner's notifications about reports."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from database.repository import Repository
from deps import get_current_user, get_repo, require_visible_collection
from schemas import ReceivedReportOut, ReportCreate

router = APIRouter(prefix="/api", tags=["reports"])


def _own_collections(repo: Repository, user: dict) -> dict[str, dict]:
    """The user's collections by ID."""
    return {str(c["id"]): c for c in repo.list_collections() if c.get("owner_id") == user["id"]}


@router.post("/collections/{collection_id}/reports", status_code=201)
def report_collection(collection_id: UUID, payload: ReportCreate,
                      repo: Repository = Depends(get_repo),
                      user: dict = Depends(get_current_user)):
    """Report someone else's collection. Each user can report a collection once."""
    collection = require_visible_collection(repo, str(collection_id), user)
    if collection.get("owner_id") == user["id"]:
        raise HTTPException(status_code=400, detail="You cannot report your own collection")
    if repo.has_reported(str(collection_id), user["id"]):
        raise HTTPException(status_code=409, detail="You have already reported this collection")
    details = (payload.details or "").strip() or None
    repo.create_report(str(collection_id), user["id"], payload.reason, details)
    return {"detail": "Thank you. The report has been sent to the owner."}


@router.get("/reports/received", response_model=list[ReceivedReportOut])
def received_reports(repo: Repository = Depends(get_repo),
                     user: dict = Depends(get_current_user)):
    """Reports on the user's own collections, newest first. Reporters stay anonymous."""
    collections = _own_collections(repo, user)
    return [
        {"id": r["id"], "collection_id": r["collection_id"],
         "collection_name": collections[str(r["collection_id"])]["name"],
         "reason": r["reason"], "details": r.get("details"),
         "created_at": r.get("created_at"), "read": r.get("read_at") is not None}
        for r in repo.list_reports_for_collections(list(collections))
    ]


@router.post("/reports/received/read", status_code=204)
def mark_received_reports_read(repo: Repository = Depends(get_repo),
                               user: dict = Depends(get_current_user)):
    """Mark all reports on the user's collections as read."""
    repo.mark_reports_read(list(_own_collections(repo, user)))
    return Response(status_code=204)
