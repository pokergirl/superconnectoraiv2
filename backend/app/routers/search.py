from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, AsyncGenerator
from pydantic import BaseModel
from uuid import UUID
import json
import asyncio
from datetime import datetime

from app.services.auth_service import get_current_user
from app.services import connections_service, search_history_service
from app.services.ai_service import search_connections
from app.services.retrieval_service import retrieval_service
from app.models.search_history import SearchHistoryCreate
from app.core.db import get_database

router = APIRouter()

class SearchFilters(BaseModel):
    industries: Optional[List[str]] = None
    company_sizes: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None

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
    current_user: dict = Depends(get_current_user),
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
        user_id = current_user["id"]
        
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
            search_results.append(SearchResult(
                connection=result["profile"],
                score=result["score"],
                summary=result["pro"],  # Use pro as summary
                pros=[result["pro"]],
                cons=[result["con"]]
            ))
        
        # Save search to history
        try:
            history_entry = SearchHistoryCreate(
                query=search_request.query,
                filters=search_request.filters.model_dump() if search_request.filters else None,
                results_count=len(search_results)
            )
            await search_history_service.create_search_history_entry(db, UUID(user_id), history_entry)
        except Exception as history_error:
            print(f"Failed to save search history: {history_error}")
            # Don't fail the search if history saving fails
        
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
    current_user: dict = Depends(get_current_user),
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
            user_id = current_user["id"]
            
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
                    search_results.append({
                        "connection": result["profile"],
                        "score": result["score"],
                        "summary": result["pro"],
                        "pros": [result["pro"]],
                        "cons": [result["con"]]
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
                await search_history_service.create_search_history_entry(db, UUID(user_id), history_entry)
            except Exception as history_error:
                print(f"Failed to save search history: {history_error}")
            
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

def convert_search_filters_to_pinecone_filter(filters: SearchFilters) -> dict:
    """Convert SearchFilters to Pinecone metadata filter format"""
    filter_dict = {}
    
    if filters.industries:
        filter_dict["company_industry"] = {"$in": filters.industries}
    
    if filters.company_sizes:
        filter_dict["company_size"] = {"$in": filters.company_sizes}
    
    if filters.locations:
        # For locations, we might need to check city, state, or country
        location_conditions = []
        for location in filters.locations:
            location_conditions.extend([
                {"city": {"$eq": location}},
                {"state": {"$eq": location}},
                {"country": {"$eq": location}}
            ])
        if location_conditions:
            filter_dict["$or"] = location_conditions
    
    # Note: Date range and follower filters would need to be handled differently
    # in Pinecone as they require numeric comparisons
    
    return filter_dict if filter_dict else None

def apply_search_filters(connections: List[dict], filters: SearchFilters) -> List[dict]:
    """Apply advanced filters to connection list"""
    filtered_connections = connections
    
    # Filter by industries
    if filters.industries:
        filtered_connections = [
            conn for conn in filtered_connections
            if conn.get('company_industry') and any(
                industry.lower() in conn.get('company_industry', '').lower()
                for industry in filters.industries
            )
        ]
    
    # Filter by company sizes
    if filters.company_sizes:
        filtered_connections = [
            conn for conn in filtered_connections
            if conn.get('company_size') and conn.get('company_size') in filters.company_sizes
        ]
    
    # Filter by locations
    if filters.locations:
        filtered_connections = [
            conn for conn in filtered_connections
            if conn.get('city') and any(
                location.lower() in conn.get('city', '').lower() or
                location.lower() in conn.get('state', '').lower() or
                location.lower() in conn.get('country', '').lower()
                for location in filters.locations
            )
        ]
    
    # Filter by connection date range
    if filters.date_range_start or filters.date_range_end:
        filtered_connections = [
            conn for conn in filtered_connections
            if is_connection_in_date_range(conn, filters.date_range_start, filters.date_range_end)
        ]
    
    # Filter by follower count
    if filters.min_followers is not None or filters.max_followers is not None:
        filtered_connections = [
            conn for conn in filtered_connections
            if is_follower_count_in_range(conn, filters.min_followers, filters.max_followers)
        ]
    
    return filtered_connections

def is_connection_in_date_range(connection: dict, start_date: Optional[str], end_date: Optional[str]) -> bool:
    """Check if connection date is within specified range"""
    connected_on = connection.get('connected_on')
    if not connected_on:
        return False
    
    try:
        # Parse connection date (assuming format like "2023-01-15" or similar)
        conn_date = datetime.fromisoformat(connected_on.replace('Z', ''))
        
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