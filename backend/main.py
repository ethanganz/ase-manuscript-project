from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import auth, collections, documents, names
from routes import map as map_routes

app = FastAPI(title="ASE Manuscript Project")

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
