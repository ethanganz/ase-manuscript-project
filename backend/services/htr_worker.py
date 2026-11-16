"""Reads uploaded pages line by line with the HTR-NLP pipeline, in the background.

How it works
  1. enqueue_page() marks a page "queued" and hands it to ONE background thread
     (one, because every run loads the models and needs a lot of memory).
  2. The thread downloads the page image from storage into a temporary folder
     and starts HTR-NLP/scripts/run_page_pipeline.py as a separate program:
        contour line segmentation -> TrOCR (one line at a time) -> place finding
  3. It reads page_response.json, stores one row per line, and marks the page
     "complete". Any problem marks the page "failed" with a readable reason.

Page status:  pending -> queued -> running -> complete | failed

The pipeline is started with an argument list (never a shell string) and files
get fixed names, so nothing a user uploads can reach a command line.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import config
from database.repository import Repository
from services.storage import ObjectStorage

logger = logging.getLogger("uvicorn.error")

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="htr")
_active: set[str] = set()  # page ids that are queued or running in THIS process
_lock = threading.Lock()


class HtrError(Exception):
    """A readable reason why a page could not be recognised."""


# --------------------------------------------------------------------------
# Setup helpers
# --------------------------------------------------------------------------
def _python() -> str:
    if config.HTR_PYTHON:
        return config.HTR_PYTHON
    venv = config.HTR_PIPELINE_DIR / ".venv-nlp" / "bin" / "python"
    return str(venv) if venv.is_file() else sys.executable


def _script() -> Path:
    return config.HTR_PIPELINE_DIR / "scripts" / "run_page_pipeline.py"


def _last_line(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return lines[-1][:500] if lines else ""


# --------------------------------------------------------------------------
# Running the pipeline
# --------------------------------------------------------------------------
def _run_pipeline(image: Path, out_dir: Path, page_id: str) -> dict:
    """Run the pipeline on one image file. Returns the parsed page_response.json."""
    if not _script().is_file():
        raise HtrError(f"Pipeline script not found: {_script()}")
    cmd = [
        _python(),
        str(_script()),
        "--image",
        str(image),
        "--output-dir",
        str(out_dir),
        "--page-id",
        page_id,
        "--device",
        config.HTR_DEVICE,
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=config.HTR_PIPELINE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,  # so a timeout can stop the whole process group
    )
    try:
        _, stderr = proc.communicate(timeout=config.HTR_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, AttributeError):  # no process groups on Windows
            proc.kill()
        proc.communicate()
        raise HtrError(f"Recognition took longer than {config.HTR_TIMEOUT_SECONDS} seconds")

    if proc.returncode != 0:
        logger.error("HTR pipeline failed for page %s:\n%s", page_id, stderr)
        # The last stderr line is the Python error message, e.g.
        # "ValueError: No text lines found; ..."
        raise HtrError(_last_line(stderr) or f"Pipeline exited with code {proc.returncode}")

    result = out_dir / "page_response.json"
    if not result.is_file():
        raise HtrError("Pipeline finished but produced no result file")
    return json.loads(result.read_text(encoding="utf-8"))


def to_rows(payload: dict) -> list[dict]:
    """page_response.json lines -> rows for the page_lines table."""
    rows = []
    for index, line in enumerate(payload.get("lines", [])):
        rows.append(
            {
                "line_index": index,
                "text": line.get("text") or "",
                "bbox": line.get("bbox"),
                "polygon": line.get("polygon"),
                "places": line.get("places") or [],
            }
        )
    return rows


def process_page(repo: Repository, storage: ObjectStorage, page_id: str) -> None:
    """Recognise one page and store the result. Never raises: failures are stored."""
    try:
        page = repo.get_page(page_id)
        if page is None:
            return
        repo.set_page_status(page_id, "running")
        data = storage.download(page["image_path"])
        if data is None:
            raise HtrError("The page image file is missing from storage")

        with tempfile.TemporaryDirectory() as work:
            image = Path(work) / ("page" + (Path(page["image_path"]).suffix or ".png"))
            image.write_bytes(data)
            payload = _run_pipeline(image, Path(work) / "result", page_id)

        info = payload.get("page", {})
        repo.save_page_lines(page_id, to_rows(payload), info.get("width"), info.get("height"))
    except HtrError as exc:
        repo.set_page_status(page_id, "failed", str(exc))
    except Exception as exc:
        logger.exception("HTR crashed for page %s", page_id)
        repo.set_page_status(page_id, "failed", f"Unexpected error: {exc}"[:500])


# --------------------------------------------------------------------------
# Queue
# --------------------------------------------------------------------------
def _job(repo: Repository, storage: ObjectStorage, page_id: str) -> None:
    try:
        process_page(repo, storage, page_id)
    finally:
        with _lock:
            _active.discard(page_id)


def enqueue_page(repo: Repository, storage: ObjectStorage, page_id: str) -> bool:
    """Queue one page. False if recognition is off or the page is already queued."""
    if not config.HTR_ENABLED:
        return False
    with _lock:
        if page_id in _active:
            return False
        _active.add(page_id)
    repo.set_page_status(page_id, "queued")
    _executor.submit(_job, repo, storage, page_id)
    return True


def enqueue_document(repo: Repository, storage: ObjectStorage, document_id: str) -> int:
    """Queue every page of a document that is not finished. Returns how many."""
    return sum(
        enqueue_page(repo, storage, page["id"])
        for page in repo.list_pages(document_id)
        if page["status"] != "complete"
    )


def recover(repo: Repository, storage: ObjectStorage) -> int:
    """After a restart: put pages that were queued or running back in the queue."""
    if not config.HTR_ENABLED:
        return 0
    return sum(enqueue_page(repo, storage, page["id"]) for page in repo.list_stuck_pages())
