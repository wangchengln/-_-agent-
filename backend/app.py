"""Fufan-OpenClaw Backend — FastAPI Entry Point"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _warm_memory_index(base_dir: Path) -> None:
    from graph.memory_indexer import get_memory_indexer

    t0 = time.perf_counter()
    indexer = get_memory_indexer(base_dir)
    indexer.ensure_ready()
    print(f"Memory index ready in {time.perf_counter() - t0:.2f}s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: scan skills, initialize agent; memory index loads in background."""
    from tools.skills_scanner import scan_skills
    from graph.agent import agent_manager

    t0 = time.perf_counter()
    scan_skills(BASE_DIR)
    agent_manager.initialize(BASE_DIR)
    print(f"Core startup in {time.perf_counter() - t0:.2f}s")

    # Memory index can call embedding APIs — never block HTTP readiness on it.
    if os.getenv("SKIP_MEMORY_INDEX_ON_STARTUP", "").lower() in ("1", "true", "yes"):
        print("Memory index warm-up skipped (SKIP_MEMORY_INDEX_ON_STARTUP)")
    else:
        asyncio.create_task(asyncio.to_thread(_warm_memory_index, BASE_DIR))

    print("fufan OpenClaw backend ready")
    yield


app = FastAPI(title="fufan OpenClaw", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.chat import router as chat_router
from api.recommend import router as recommend_router
from api.files import router as files_router
from api.sessions import router as sessions_router
from api.tokens import router as tokens_router
from api.compress import router as compress_router
from api.config_api import router as config_router
from api.itinerary import router as itinerary_router
from api.poi import router as poi_router

app.include_router(chat_router, prefix="/api")
app.include_router(recommend_router, prefix="/api")
app.include_router(itinerary_router, prefix="/api")
app.include_router(poi_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(tokens_router, prefix="/api")
app.include_router(compress_router, prefix="/api")
app.include_router(config_router, prefix="/api")


@app.get("/")
async def root():
    return {"name": "fufan OpenClaw", "version": "0.1.0", "status": "running"}
