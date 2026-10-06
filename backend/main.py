
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import documents, names

app = FastAPI(
    title="ASE Manuscript Project"
)

# CORS middleware - change in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(names.router)
app.include_router(documents.router)
