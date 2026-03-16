"""
FastAPI Application Entry Point
---------------------------------
Main application setup with CORS, static file mounting,
and router registration.
"""

import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Data Extraction Platform",
    description=(
        "A production-ready web scraping and data extraction platform "
        "with AI-assisted automation, data validation, and structured exports."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
from app.api.routes import router as api_router  # noqa: E402
app.include_router(api_router)

# Mount static files for the frontend
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the frontend dashboard."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "AI Data Extraction Platform",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    # Ensure data directories exist
    os.makedirs("data/exports", exist_ok=True)
    logger.info("🚀 AI Data Extraction Platform started")
    logger.info(f"   Frontend: {FRONTEND_DIR}")
    logger.info(f"   Docs: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown cleanup."""
    logger.info("Shutting down AI Data Extraction Platform")
