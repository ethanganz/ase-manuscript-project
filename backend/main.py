from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from routes import auth, collections, documents, names, reports
from routes import map as map_routes


@asynccontextmanager
async def lifespan(application: FastAPI):
    # After a restart, pages that were queued or running continue where they stopped.
    if config.HTR_ENABLED:
        from deps import get_repo, get_storage
        from services import htr_worker

        overrides = application.dependency_overrides  # tests swap in fakes here
        repo = overrides.get(get_repo, get_repo)()
        storage = overrides.get(get_storage, get_storage)()
        htr_worker.recover(repo, storage)
    yield


app = FastAPI(title="ASE Manuscript Project", lifespan=lifespan)

# CORS middleware - change in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(names.router)
app.include_router(collections.router)
app.include_router(documents.router)
app.include_router(map_routes.router)
app.include_router(reports.router)
