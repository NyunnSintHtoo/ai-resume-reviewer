"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .routers import auth, history, reviews
from .services.rag import get_knowledge_base

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    kb = get_knowledge_base()  # warm the RAG index at startup
    logging.getLogger(__name__).info(
        "Knowledge base indexed: %d chunks", len(kb.chunks)
    )
    yield


app = FastAPI(
    title=settings.app_name,
    description="AI-powered resume review with an agentic Claude workflow and local RAG.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(reviews.router)
app.include_router(history.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    from .agents.providers import get_provider

    return {
        "status": "ok",
        "provider": get_provider().name,
        "knowledge_chunks": len(get_knowledge_base().chunks),
    }
