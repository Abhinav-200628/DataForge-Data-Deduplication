"""FastAPI application factory and server entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from deduplication.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure SQLite tables exist
    from deduplication.api.service import PipelineService
    service = PipelineService()
    service.repository._init_db()
    yield


app = FastAPI(
    title="DataForge Deduplication API",
    description="RESTful enterprise backend for Customer and Product Master Data Management (MDM) Deduplication.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for local Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", include_in_schema=False)
def root():
    return JSONResponse({
        "service": "DataForge Data Deduplication API",
        "version": "0.1.0",
        "documentation": "/docs",
        "health": "/api/health",
    })

