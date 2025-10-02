from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, AsyncGenerator
from pydantic import BaseModel
from uuid import UUID
import json
import asyncio
from datetime import datetime

from app.services.auth_service import get_current_user
from app.services import connections_service, search_history_service, last_search_results_service
from app.services.ai_service import search_connections
from app.services.retrieval_service import retrieval_service
from app.models.search_history import SearchHistoryCreate
from app.models.last_search_results import LastSearchResultsCreate
from app.models.user import UserPublic
from app.core.db import get_database

router = APIRouter()

class SearchFilters(BaseModel):
    # Streamlined filters - only Open to Work and Country
    open_to_work: Optional[bool] = None
    country: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    filters: Optional[SearchFilters] = None

class SearchResult(BaseModel):
    connection: dict
    score: int
    summary: str
    pros: list
    cons: list

@router.post("/search", response_model=List[SearchResult])
async def ai_search_connections(
    search_request: SearchRequest,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(20, ge=1, le=100, description="Number of results per page"),
    current_user: UserPublic = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Perform AI-powered search on user's connections using the new retrieval service
    """
    if not search_request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )
    
    try:
        user_id = current_user.id
        
        # Convert filters to the format expected by the retrieval service
        filter_dict = None
        if search_request.filters:
            filter_dict = convert_search_filters_to_pinecone_filter(search_request.filters)
        
        # Use the new retrieval service for search and re-ranking
        reranked_results = await retrieval_service.retrieve_and_rerank(
            user_query=search_request.query,
            user_id=user_id,
            enable_query_rewrite=True,
            filter_dict=filter_dict
        )
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = reranked_results[start_idx:end_idx]
        
        # Convert to the expected SearchResult format
        search_results = []
        for result in paginated_results:
            # Use enhanced pros and cons if available, fallback to single pro/con
            pros = result.get("pros", [result.get("pro", "Strong candidate match.")])
            cons = result.get("cons", [result.get("con", "Some limitations may apply.")])
            
            search_results.append(SearchResult(
                connection=result["profile"],
                score=result["score"],
                summary=result.get("pro", pros[0] if pros else "Strong candidate match."),  # Use first pro as summary
                pros=pros,
                cons=cons
            ))
        
        # Save search to history
        try:
            history_entry = SearchHistoryCreate(
                query=search_request.query,
                filters=search_request.filters.model_dump() if search_request.filters else None,
                results_count=len(search_results)
            )
            await search_history_service.create_search_history_entry(db, user_id, history_entry)
        except Exception as history_error:
            print(f"Failed to save search history: {history_error}")
            # Don't fail the search if history saving fails
        
        # Save as last search results for persistence across sessions
        if getattr(current_user, "persist_search_results", True):
            try:
                last_search_entry = LastSearchResultsCreate(
                    query=search_request.query,
                    filters=search_request.filters.model_dump() if search_request.filters else None,
                    results=[result.model_dump() for result in search_results],
                    results_count=len(search_results),
                    page=page,
                    page_size=page_size
                )
                await last_search_results_service.save_last_search_results(db, user_id, last_search_entry)
            except Exception as last_search_error:
                print(f"Failed to save last search results: {last_search_error}")
                # Don't fail the search if last search saving fails
        
        return search_results
        
    except Exception as e:
        print(f"Search router error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.post("/search/stream")
async def ai_search_connections_stream(
    search_request: SearchRequest,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(20, ge=1, le=100, description="Number of results per page"),
    current_user: UserPublic = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Perform AI-powered search with streaming results using Server-Sent Events
    """
    if not search_request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )
    
    async def generate_search_stream() -> AsyncGenerator[str, None]:
        try:
            user_id = current_user.id
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting search...'})}\n\n"
            
            # Convert filters to the format expected by the retrieval service
            filter_dict = None
            if search_request.filters:
                filter_dict = convert_search_filters_to_pinecone_filter(search_request.filters)
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating query embedding...'})}\n\n"
            
            # Use the new retrieval service for search and re-ranking
            reranked_results = await retrieval_service.retrieve_and_rerank(
                user_query=search_request.query,
                user_id=user_id,
                enable_query_rewrite=True,
                filter_dict=filter_dict
            )
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'Found {len(reranked_results)} results, applying pagination...'})}\n\n"
            
            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_results = reranked_results[start_idx:end_idx]
            
            # Stream results in chunks
            chunk_size = 5  # Send 5 results at a time
            for i in range(0, len(paginated_results), chunk_size):
                chunk = paginated_results[i:i + chunk_size]
                
                # Convert to the expected SearchResult format
                search_results = []
                for result in chunk:
                    # Use enhanced pros and cons if available, fallback to single pro/con
                    pros = result.get("pros", [result.get("pro", "Strong candidate match.")])
                    cons = result.get("cons", [result.get("con", "Some limitations may apply.")])
                    
                    search_results.append({
                        "connection": result["profile"],
                        "score": result["score"],
                        "summary": result.get("pro", pros[0] if pros else "Strong candidate match."),
                        "pros": pros,
                        "cons": cons
                    })
                
                # Send chunk of results
                yield f"data: {json.dumps({'type': 'results', 'data': search_results, 'chunk': i//chunk_size + 1})}\n\n"
                
                # Small delay to simulate streaming
                await asyncio.sleep(0.1)
            
            # Save search to history
            try:
                history_entry = SearchHistoryCreate(
                    query=search_request.query,
                    filters=search_request.filters.model_dump() if search_request.filters else None,
                    results_count=len(paginated_results)
                )
                await search_history_service.create_search_history_entry(db, user_id, history_entry)
            except Exception as history_error:
                print(f"Failed to save search history: {history_error}")
            
            # Save as last search results for persistence across sessions
            try:
                # Convert search results to the format expected by LastSearchResultsCreate
                search_results_for_last_search = []
                for result in paginated_results:
                    pros = result.get("pros", [result.get("pro", "Strong candidate match.")])
                    cons = result.get("cons", [result.get("con", "Some limitations may apply.")])
                    
                    search_results_for_last_search.append({
                        "connection": result["profile"],
                        "score": result["score"],
                        "summary": result.get("pro", pros[0] if pros else "Strong candidate match."),
                        "pros": pros,
                        "cons": cons
                    })
                
                last_search_entry = LastSearchResultsCreate(
                    query=search_request.query,
                    filters=search_request.filters.model_dump() if search_request.filters else None,
                    results=search_results_for_last_search,
                    results_count=len(paginated_results),
                    page=page,
                    page_size=page_size
                )
                await last_search_results_service.save_last_search_results(db, user_id, last_search_entry)
            except Exception as last_search_error:
                print(f"Failed to save last search results: {last_search_error}")
            
            # Send completion message
            yield f"data: {json.dumps({'type': 'complete', 'total_results': len(paginated_results)})}\n\n"
            
        except Exception as e:
            print(f"Streaming search error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Search failed: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate_search_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.post("/search/progress")
async def ai_search_connections_progress(
    search_request: SearchRequest,
    current_user: UserPublic = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Perform AI-powered search with progress updates.
    """
    if not search_request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )

    async def progress_generator():
        # Simulate progress
        for i in range(5):
            await asyncio.sleep(0.5)
            yield f"data: {json.dumps({'progress': (i + 1) * 10})}\n\n"

        # Perform the actual search
        try:
            user_id = current_user.id
            
            filter_dict = None
            if search_request.filters:
                filter_dict = convert_search_filters_to_pinecone_filter(search_request.filters)
            
            yield f"data: {json.dumps({'progress': 60, 'message': 'Reranking results...'})}\n\n"
            await asyncio.sleep(1)

            reranked_results = await retrieval_service.retrieve_and_rerank(
                user_query=search_request.query,
                user_id=user_id,
                enable_query_rewrite=True,
                filter_dict=filter_dict
            )

            yield f"data: {json.dumps({'progress': 80, 'message': 'Finalizing...'})}\n\n"
            await asyncio.sleep(1)

            search_results = []
            for result in reranked_results:
                pros = result.get("pros", [result.get("pro", "Strong candidate match.")])
                cons = result.get("cons", [result.get("con", "Some limitations may apply.")])
                
                search_results.append(SearchResult(
                    connection=result["profile"],
                    score=result["score"],
                    summary=result.get("pro", pros[0] if pros else "Strong candidate match."),
                    pros=pros,
                    cons=cons
                ).model_dump())

            # Save search to history
            try:
                history_entry = SearchHistoryCreate(
                    query=search_request.query,
                    filters=search_request.filters.model_dump() if search_request.filters else None,
                    results_count=len(search_results)
                )
                await search_history_service.create_search_history_entry(db, user_id, history_entry)
            except Exception as history_error:
                print(f"Failed to save search history: {history_error}")

            # Save as last search results for persistence across sessions
            try:
                last_search_entry = LastSearchResultsCreate(
                    query=search_request.query,
                    filters=search_request.filters.model_dump() if search_request.filters else None,
                    results=search_results,
                    results_count=len(search_results),
                    page=1,  # Progress endpoint doesn't use pagination
                    page_size=len(search_results)
                )
                await last_search_results_service.save_last_search_results(db, user_id, last_search_entry)
            except Exception as last_search_error:
                print(f"Failed to save last search results: {last_search_error}")

            yield f"data: {json.dumps({'progress': 100, 'results': search_results})}\n\n"

        except Exception as e:
            print(f"Search router error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(progress_generator(), media_type="text/event-stream")

def convert_search_filters_to_pinecone_filter(filters: SearchFilters) -> dict:
    """Convert streamlined SearchFilters to Pinecone metadata filter format"""
    filter_dict = {}
    
    # Open to Work filter
    if filters.open_to_work is not None:
        filter_dict["is_open_to_work"] = {"$eq": filters.open_to_work}
    
    # Country filter
    if filters.country:
        filter_dict["country"] = {"$eq": filters.country}
    
    return filter_dict if filter_dict else None

def apply_search_filters(connections: List[dict], filters: SearchFilters) -> List[dict]:
    """Apply streamlined filters to connection list"""
    filtered_connections = connections
    
    # Filter by Open to Work status
    if filters.open_to_work is not None:
        filtered_connections = [
            conn for conn in filtered_connections
            if conn.get('is_open_to_work') == filters.open_to_work or conn.get('isOpenToWork') == filters.open_to_work
        ]
    
    # Filter by Country
    if filters.country:
        filtered_connections = [
            conn for conn in filtered_connections
            if conn.get('country') and conn.get('country').lower() == filters.country.lower()
        ]
    
    return filtered_connections

def is_connection_in_date_range(connection: dict, start_date: Optional[str], end_date: Optional[str]) -> bool:
    """Check if connection date is within specified range"""
    connected_on = connection.get('connected_on')
    if not connected_on:
        return False
    
    try:
        # Parse connection date (assuming format like "2023-01-15" or similar)
        conn_date = datetime.fromisoformat(connected_on)
        
        if start_date:
            start = datetime.fromisoformat(start_date)
            if conn_date < start:
                return False
        
        if end_date:
            end = datetime.fromisoformat(end_date)
            if conn_date > end:
                return False
        
        return True
    except (ValueError, AttributeError):
        return False

def is_follower_count_in_range(connection: dict, min_followers: Optional[int], max_followers: Optional[int]) -> bool:
    """Check if follower count is within specified range"""
    followers_str = connection.get('followers')
    if not followers_str:
        return False
    
    try:
        # Extract numeric value from followers string (e.g., "1,234" -> 1234)
        followers_count = int(followers_str.replace(',', '').replace('+', ''))
        
        if min_followers is not None and followers_count < min_followers:
            return False
        
        if max_followers is not None and followers_count > max_followers:
            return False
        
        return True
    except (ValueError, AttributeError):
        return False