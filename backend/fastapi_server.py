"""
RepoRAG FastAPI Application

AI Codebase Intelligence Engine
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ============================================================
# Database
# ============================================================

from app.core.database import Base, engine

# Import all models so SQLAlchemy registers them with Base.metadata
import app.models
from app.core.redis import init_redis, close_redis
from app.middleware.redis_stream import RedisResponseStreamMiddleware


# ============================================================
# API Routers
# ============================================================

from app.api.v1.auth import router as auth_router
from app.api.v1.repositories import router as repositories_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.analysis import router as analysis_router
# Search and Chat routers are intentionally not imported to keep internal
# endpoints out of the public API surface.
from app.api.v1.graph import router as graph_router
from app.api.v1.debug import router as debug_router


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"


# ============================================================
# Application Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup/shutdown lifecycle.

    Startup:
        - Connect to PostgreSQL
        - Create missing database tables

    Shutdown:
        - Dispose database engine
    """

    print("=" * 70)
    print("Starting RepoRAG...")
    print("=" * 70)

    try:
        # ----------------------------------------------------
        # Create database tables
        # ----------------------------------------------------
        async with engine.begin() as connection:
            await connection.run_sync(
                Base.metadata.create_all
            )

        print("✓ Database tables verified/created")

        # Initialize Redis
        try:
            await init_redis()
            print("✓ Redis connected")
        except Exception as exc:
            print("✗ Redis initialization failed")
            print(f"  Error: {exc}")

    except Exception as exc:
        print("✗ Database initialization failed")
        print(f"  Error: {exc}")

        # Re-raise so the application does not start
        # with a broken database configuration.
        raise

    print("✓ RepoRAG startup completed")
    print("=" * 70)
    

    yield

    # --------------------------------------------------------
    # Application shutdown
    # --------------------------------------------------------

    print("=" * 70)
    print("Shutting down RepoRAG...")
    print("=" * 70)

    await engine.dispose()

    # Close Redis connection
    try:
        await close_redis()
        print("✓ Redis connection closed")
    except Exception:
        pass

    print("✓ Database connection closed")


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="RepoRAG",
    description="""
# RepoRAG — AI Codebase Intelligence Engine

RepoRAG is an AI-powered codebase intelligence backend that allows
developers to connect GitHub repositories and ask questions about
their entire codebase.

## Core capabilities

- GitHub OAuth authentication
- GitHub repository discovery
- Repository ingestion
- Source-code parsing
- AST-aware analysis
- Code chunking
- Symbol extraction
- Import analysis
- Embedding generation
- PostgreSQL + pgvector semantic search
- Hybrid code search
- Dependency graph generation
- Repository analysis
- RAG-powered codebase questions
- AI-generated explanations

## Architecture

GitHub Repository
→ Repository Ingestion
→ Source Code Parsing
→ AST Analysis
→ Code Chunking
→ Embeddings
→ PostgreSQL + pgvector
→ Retrieval
→ Reranking
→ Context Building
→ LLM
→ AI Codebase Answer

## AI Stack

- LLM: Groq
- Embeddings: Gemini
- Vector Database: PostgreSQL + pgvector
- Cache / Queue: Redis
- Code Parser: Tree-sitter / AST
- Repository Provider: GitHub API
- Backend: FastAPI
""",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# Register Redis response stream middleware
app.add_middleware(RedisResponseStreamMiddleware)


# ============================================================
# Static Files
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


# ============================================================
# API Router Configuration
# ============================================================

API_PREFIX = "/api/v1"


# ------------------------------------------------------------
# Authentication
# ------------------------------------------------------------

app.include_router(
    auth_router,
    prefix=API_PREFIX,
    tags=["Authentication"],
)


# ------------------------------------------------------------
# Repositories
# ------------------------------------------------------------

app.include_router(
    repositories_router,
    prefix=API_PREFIX,
    tags=["Repositories"],
)


# ------------------------------------------------------------
# Repository Ingestion
# ------------------------------------------------------------

app.include_router(
    ingestion_router,
    prefix=API_PREFIX,
    tags=["Ingestion"],
)


# ------------------------------------------------------------
# Repository Analysis
# ------------------------------------------------------------

app.include_router(
    analysis_router,
    prefix=API_PREFIX,
    tags=["Analysis"],
)




# Search and Chat routers are intentionally excluded from the FastAPI
# application to comply with the requested public API surface.


# ------------------------------------------------------------
# Dependency Graph
# ------------------------------------------------------------

app.include_router(
    graph_router,
    prefix=API_PREFIX,
    tags=["Dependency Graph"],
)


# ------------------------------------------------------------
# Debug
# ------------------------------------------------------------

# Hide debug endpoints from OpenAPI/Swagger UI (internal only)
app.include_router(
    debug_router,
    prefix=API_PREFIX,
    include_in_schema=False,
)


# ============================================================
# Landing Page
# ============================================================

@app.get(
    "/",
    include_in_schema=False,
)
async def landing_page():
    """
    Professional RepoRAG project landing page.
    """

    return FileResponse(
        TEMPLATES_DIR / "landing.html"
    )


# ============================================================
# Favicon
# ============================================================

@app.get(
    "/favicon.ico",
    include_in_schema=False,
)
async def favicon():
    """
    Serve RepoRAG favicon.
    """

    return FileResponse(
        STATIC_DIR / "favicon.ico"
    )


# ============================================================
# Health Check
# ============================================================

@app.get(
    "/health",
    tags=["System"],
)
async def health():
    """
    Check whether the RepoRAG API is running.
    """

    return {
        "status": "healthy",
        "service": "reporag",
        "version": "0.1.0",
    }


# ============================================================
# Application Entry Point
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fastapi_server:app",
        host="127.0.0.1",
        port=9001,
        reload=True,
    )