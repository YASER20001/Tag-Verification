"""
Tag Verify — FastAPI backend entry point.
"""
import sys
import os

# Ensure server/ is on the path so sibling imports work
sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db.database import init_db
from routes.tags import router as tags_router
from routes.documents import router as documents_router
from routes.relationships import router as relationships_router
from routes.dashboard import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Tag Verify API",
    version="1.0.0",
    description="Engineering Tag Verification System",
    lifespan=lifespan,
)

# CORS — allow the React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(tags_router)
app.include_router(documents_router)
app.include_router(relationships_router)
app.include_router(dashboard_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Tag Verify API"}


# Serve static uploads
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
