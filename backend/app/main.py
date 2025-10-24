import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.db import connect_to_mongo, close_mongo_connection
from app.core.config import settings
from app.services.threading_service import threading_service
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.routers import auth, connections, search, saved_searches, search_history, favorites, embeddings, pinecone_index, retrieval, generated_emails, tips, warm_intro_requests, health, invitations, follow_up_emails, filter_options, public, access_requests, dashboard_stats, last_search_results, user_preferences, email, access_request_follow_ups

# Get the logger used by Uvicorn
uvicorn_error_logger = logging.getLogger("uvicorn.error")
# Set the logger level to DEBUG
uvicorn_error_logger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # on startup
    await connect_to_mongo()
    
    logger.info("Starting up...")
    
    threading_service.start()
    await start_scheduler()
    yield
    # on shutdown
    await stop_scheduler()
    await close_mongo_connection()
    threading_service.stop()

app = FastAPI(lifespan=lifespan)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://superconnectoraiv2-snax.vercel.app", "https://superconnectai.com", "https://www.superconnectai.com"],  # Allows frontend origins
    allow_credentials=True,  # Can be True when specific origins are listed
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
app.include_router(pinecone_index.router, prefix="/api/v1", tags=["Pinecone Index"])
app.include_router(retrieval.router, prefix="/api/v1", tags=["Retrieval"])
app.include_router(generated_emails.router, prefix="/api/v1", tags=["generated-emails"])
app.include_router(tips.router, prefix="/api/v1", tags=["Tipping"])
app.include_router(warm_intro_requests.router, prefix="/api/v1", tags=["Warm Intro Requests"])
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(invitations.router, prefix="/api/v1", tags=["Invitations"])
app.include_router(follow_up_emails.router, prefix="/api/v1", tags=["Follow-up Emails"])
app.include_router(filter_options.router, prefix="/api/v1", tags=["Filter Options"])
app.include_router(public.router, prefix="/api/v1", tags=["Public"])
app.include_router(access_requests.router, prefix="/api/v1", tags=["Access Requests"])
app.include_router(dashboard_stats.router, prefix="/api/v1", tags=["Dashboard Stats"])
app.include_router(last_search_results.router, prefix="/api/v1", tags=["Last Search Results"])
app.include_router(user_preferences.router, prefix="/api/v1", tags=["User Preferences"])
app.include_router(email.router, prefix="/api/v1", tags=["Email"])
app.include_router(access_request_follow_ups.router, tags=["Access Request Follow-ups"])
app.include_router(access_requests.public_router, prefix="/api/v1", tags=["Access Requests"])
