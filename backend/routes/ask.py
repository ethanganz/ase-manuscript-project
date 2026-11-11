from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from database.repository import Repository
from deps import get_llm, get_repo
from schemas import AskRequest, AskResponse
from services.ask import answer_question
from services.llm import LLM, LLMRateLimited, LLMUnavailable

router = APIRouter(prefix="/api/collections", tags=["ask"])


# Plain `def` (not async): the call to the language model blocks, so FastAPI runs
# this in a worker thread and other requests are not held up.
@router.post("/{collection_id}/ask", response_model=AskResponse)
def ask(
    collection_id: UUID,
    payload: AskRequest,
    repo: Repository = Depends(get_repo),
    llm: LLM = Depends(get_llm),
):
    """Answer a question using only the transcript lines of this collection.

    Errors besides the usual 404 and 422:
    * 429 - the usage limit is reached. The body has ``retry_after_seconds`` and the
      ``Retry-After`` header carries the same number.
    * 503 - the AI service is not configured or not working.
    """
    if repo.get_collection(str(collection_id)) is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    try:
        return answer_question(repo, llm, str(collection_id), payload.question)
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
