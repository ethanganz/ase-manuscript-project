"""HTTP service the web backend calls to read one uploaded page.

  GET  /health      {"status": "ok", "device": ...} once the models are loaded
  POST /transcribe  multipart: image=<page image>  ->  {"page": {...}, "lines": [...]}
                    422 if no text lines are found, 400 if the image is unreadable

Run from the HTR-NLP folder:  uvicorn service.app:app --port 8000
Environment: HTR_DEVICE (auto|cpu|cuda|mps), HTR_BATCH_SIZE (lines read at once, default 1).
"""
import io
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image

from service.pipeline import NoLinesFound, Pipeline

MAX_IMAGE_BYTES = 60 * 1024 * 1024

state: dict = {}
# One page at a time: the models are shared and memory is limited.
lock = threading.Lock()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    state['pipeline'] = Pipeline(
        device=os.getenv('HTR_DEVICE', 'auto'),
        batch_size=int(os.getenv('HTR_BATCH_SIZE', '1')),
    )
    yield
    state.clear()


app = FastAPI(title='Bullinger HTR service', lifespan=lifespan)


@app.get('/health')
def health():
    return {'status': 'ok', 'device': state['pipeline'].device}


# Plain `def`: recognition is slow and blocking, so FastAPI runs it in a worker thread.
@app.post('/transcribe')
def transcribe(image: UploadFile = File(...)):
    data = image.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail='Image is too large')
    try:
        page = Image.open(io.BytesIO(data))
        page.load()
    except Exception as exc:
        raise HTTPException(status_code=400, detail='Image is corrupt or unreadable') from exc
    with lock:
        try:
            return state['pipeline'].recognize(page)
        except NoLinesFound as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
