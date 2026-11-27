from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from database.repository import Repository
from deps import get_llm, get_optional_user, get_repo, require_visible_collection
from schemas import AskRequest, AskResponse
from services.ask import answer_page_question
from services.llm import LLM, LLMRateLimited, LLMUnavailable

router = APIRouter(prefix="/api/pages", tags=["ask"])


# Plain `def` (not async): the call to the language model blocks, so FastAPI runs
# this in a worker thread and other requests are not held up.
@router.post("/{page_id}/ask", response_model=AskResponse)
def ask(
    page_id: UUID,
    payload: AskRequest,
    repo: Repository = Depends(get_repo),
    llm: LLM = Depends(get_llm),
    user: dict | None = Depends(get_optional_user),
):
    """Answer a question about one page, using its transcript lines and the recent chat.

    Errors besides the usual 404 and 422:
    * 409 - the page has not been transcribed yet.
    * 429 - the usage limit is reached. The body has ``retry_after_seconds`` and the
      ``Retry-After`` header carries the same number.
    * 503 - the AI service is not configured or not working.
    """
    page = repo.get_page(str(page_id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    document = repo.get_document(page["document_id"])
    if document is None:
        raise HTTPException(status_code=404, detail="Page not found")
    require_visible_collection(repo, document["collection_id"], user)
    if page.get("status") != "complete":
        raise HTTPException(status_code=409, detail="This page has not been transcribed yet.")

    history = [turn.model_dump() for turn in payload.history]
    try:
        return answer_page_question(repo, llm, page, payload.question, history)
    except LLMRateLimited as error:
        message = (
            "The daily question limit is reached. Please try again later."
            if error.daily
            else f"The question limit is reached. Please wait {error.retry_after_seconds} seconds."
        )
        raise HTTPException(
            status_code=429,
            detail={
                "code": "llm_rate_limited",
                "message": message,
                "retry_after_seconds": error.retry_after_seconds,
                "daily": error.daily,
            },
            headers={"Retry-After": str(error.retry_after_seconds)},
        )
    except LLMUnavailable as error:
        raise HTTPException(
            status_code=503, detail={"code": "llm_unavailable", "message": str(error)}
        )
