"""HTTP wrapper around the page pipeline. The backend sends uploaded pages here.

  GET  /health      {"status": "ok"} once the models are loaded
  POST /transcribe  multipart: image=<page image>, language=de|la|unknown

Run from the htr/ folder:  uvicorn service.app:app --port 8000
Settings (environment): HTR_MODEL_DIR, HTR_DEVICE (auto|cpu|cuda|mps), HTR_BATCH_SIZE.
"""
import io
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps

from service.pipeline import ROOT, Pipeline

MAX_IMAGE_BYTES = 60 * 1024 * 1024

state: dict = {}
# One page at a time: the models are shared and a GPU has room for one batch.
lock = threading.Lock()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    state["pipeline"] = Pipeline(
        Path(os.getenv("HTR_MODEL_DIR", str(ROOT / "models/bullinger_checkpoint"))),
        device=os.getenv("HTR_DEVICE", "auto"),
        batch_size=int(os.getenv("HTR_BATCH_SIZE", "4")),
    )
    yield
    state.clear()


app = FastAPI(title="HTR service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "device": state["pipeline"].device}


# Plain `def`: recognition is slow and blocking, so FastAPI runs it in a thread.
@app.post("/transcribe")
def transcribe(
    image: UploadFile = File(...),
    language: Literal["de", "la", "unknown"] = Form("unknown"),
):
    data = image.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large")
    try:
        with Image.open(io.BytesIO(data)) as im:
            page = ImageOps.exif_transpose(im).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Image is corrupt or unreadable") from exc
    with lock:
        return state["pipeline"].recognize(page, None if language == "unknown" else language)
