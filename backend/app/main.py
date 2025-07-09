import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.db import connect_to_mongo, close_mongo_connection
from app.routers import auth, connections, search, saved_searches, search_history, favorites, embeddings, pinecone_index, retrieval

# Get the logger used by Uvicorn
uvicorn_error_logger = logging.getLogger("uvicorn.error")
# Set the logger level to DEBUG
uvicorn_error_logger.setLevel(logging.DEBUG)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # on startup
    await connect_to_mongo()
    yield
    # on shutdown
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins from all regions
    allow_credentials=False,  # Must be False when allow_origins is ["*"]
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(connections.router, prefix="/api/v1", tags=["Connections"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(saved_searches.router, prefix="/api/v1", tags=["Saved Searches"])
app.include_router(search_history.router, prefix="/api/v1", tags=["Search History"])
app.include_router(favorites.router, prefix="/api/v1", tags=["Favorites"])
app.include_router(embeddings.router, prefix="/api/v1/embeddings", tags=["Embeddings"])
app.include_router(pinecone_index.router, tags=["Pinecone Index"])
app.include_router(retrieval.router, prefix="/api/v1", tags=["Retrieval"])

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}