from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
import csv
import io

from app.services.auth_service import get_current_user, get_current_admin_user
from app.models.user import UserRole
from app.services import warm_intro_requests_service
from app.models.warm_intro_request import WarmIntroStatus
from app.services.follow_up_email_service import schedule_follow_up_email
from app.services.email_service import get_email_service
from app.core.db import get_database
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

async def send_automatic_warm_intro_notification(warm_intro_request, user_email: str, db):
    """
    Send automatic warm intro notification email to ha@nextstepfwd.com
    """
    try:
        logger.info(f"🚀 Sending automatic warm intro notification for request ID: {warm_intro_request.id}")
        
        # Create the notification email content
        subject = f"New Warm Intro Request: {warm_intro_request.requester_name} → {warm_intro_request.connection_name}"
        
        # Format the email body with all the data
        email_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2563eb; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">
            🔥 New Warm Intro Request
        </h2>
        
        <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #1f2937; margin-top: 0;">Request Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; width: 150px;">Request ID:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Status:</td>
                    <td style="padding: 8px 0;">
                        <span style="background-color: #fef3c7; color: #92400e; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                            {str(warm_intro_request.status).upper()}
                        </span>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Created:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.created_at}</td>
                </tr>
            </table>
        </div>
        
        <div style="background-color: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #1f2937; margin-top: 0;">👤 Requester Information</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; width: 150px;">Name:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.requester_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">First Name:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.requester_first_name or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Last Name:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.requester_last_name or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Email:</td>
                    <td style="padding: 8px 0;">{user_email}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">LinkedIn:</td>
                    <td style="padding: 8px 0;">
                        {f'<a href="{warm_intro_request.requester_linkedin_url}" target="_blank" style="color: #2563eb;">View Profile</a>' if warm_intro_request.requester_linkedin_url else 'N/A'}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">About:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.about or 'N/A'}</td>
                </tr>
            </table>
        </div>
        
        <div style="background-color: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #1f2937; margin-top: 0;">🎯 Connection Information</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; width: 150px;">Name:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.connection_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">First Name:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.connection_first_name or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Last Name:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.connection_last_name or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Email:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.connection_email or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">LinkedIn:</td>
                    <td style="padding: 8px 0;">
                        {f'<a href="{warm_intro_request.connection_linkedin_url}" target="_blank" style="color: #2563eb;">View Profile</a>' if warm_intro_request.connection_linkedin_url else 'N/A'}
                    </td>
                </tr>
            </table>
        </div>
        
        <div style="background-color: #fefce8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #1f2937; margin-top: 0;">💬 Request Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; width: 150px;">Reason:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.reason or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Outcome:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.outcome or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Connected Date:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.connected_date or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Declined Date:</td>
                    <td style="padding: 8px 0;">{warm_intro_request.declined_date or 'N/A'}</td>
                </tr>
            </table>
        </div>
        
        <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #1f2937; margin-top: 0;">🔗 Quick Actions</h3>
            <p style="margin: 10px 0;">
                <a href="https://superconnectorai.com/warm-intro-requests" 
                   style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    View in Admin Dashboard
                </a>
            </p>
        </div>
        
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
        <p style="color: #6b7280; font-size: 14px; margin: 0;">
            This notification was sent automatically when a new warm intro request was created.
        </p>
    </div>
</body>
</html>
        """
        
        # Get the email service
        email_service = get_email_service()
        
        # Send the email to ha@nextstepfwd.com
        success = await email_service.send_email(
            to_email="ha@nextstepfwd.com",
            subject=subject,
            body=email_body,
            html=True
        )
        
        if success:
            logger.info(f"✅ Automatic warm intro notification sent successfully to ha@nextstepfwd.com for request {warm_intro_request.id}")
        else:
            logger.error(f"❌ Failed to send automatic warm intro notification to ha@nextstepfwd.com for request {warm_intro_request.id}")
            
    except Exception as e:
        logger.error(f"❌ Error sending automatic warm intro notification: {str(e)}")
        # Don't raise the exception - we don't want email failures to break the warm intro request creation

# Pydantic models for request/response
class WarmIntroRequestCreate(BaseModel):
    requester_name: str
    connection_name: str
    status: WarmIntroStatus = WarmIntroStatus.pending
    outcome: Optional[str] = None
    connection_linkedin_url: Optional[str] = None
    connection_email: Optional[str] = None
    reason: Optional[str] = None  # Why the requester wants to connect
    about: Optional[str] = None   # About the requester
    requester_linkedin_url: Optional[str] = None  # Requester's LinkedIn profile

class WarmIntroRequestUpdate(BaseModel):
    status: WarmIntroStatus
    connected_date: Optional[datetime] = None
    declined_date: Optional[datetime] = None
    outcome: Optional[str] = None
    outcome_date: Optional[datetime] = None


class WarmIntroRequestResponse(BaseModel):
    id: str
    requester_name: str
    connection_name: str
    requester_first_name: Optional[str] = None
    requester_last_name: Optional[str] = None
    connection_first_name: Optional[str] = None
    connection_last_name: Optional[str] = None
    connection_linkedin_url: Optional[str] = None
    connection_email: Optional[str] = None
    status: WarmIntroStatus
    created_at: str
    updated_at: str
    user_id: str
    connected_date: Optional[str] = None
    declined_date: Optional[str] = None
    outcome: Optional[str] = None
    outcome_date: Optional[str] = None

class PaginatedWarmIntroRequestsResponse(BaseModel):
    items: List[WarmIntroRequestResponse]
    total: int
    page: int
    limit: int
    total_pages: int
    status_counts: dict = {}

@router.post("/warm-intro-requests/", response_model=WarmIntroRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_warm_intro_request(
    request: WarmIntroRequestCreate,
    current_user = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Create a new warm intro request.
    
    Requires authentication. The request will be associated with the current user.
    """
    user_id = UUID(str(current_user.id))
    
    try:
        warm_intro_request = await warm_intro_requests_service.create_warm_intro_request(
            db=db,
            user_id=user_id,
            requester_name=request.requester_name,
            connection_name=request.connection_name,
            status=request.status,
            connection_linkedin_url=request.connection_linkedin_url,
            connection_email=request.connection_email,
            reason=request.reason,
            about=request.about,
            requester_linkedin_url=request.requester_linkedin_url
        )
        
        # Send automatic notification email to ha@nextstepfwd.com
        await send_automatic_warm_intro_notification(warm_intro_request, current_user.email, db)
        
        return WarmIntroRequestResponse(
            id=str(warm_intro_request.id),
            requester_name=warm_intro_request.requester_name,
            connection_name=warm_intro_request.connection_name,
            requester_first_name=warm_intro_request.requester_first_name,
            requester_last_name=warm_intro_request.requester_last_name,
            connection_first_name=warm_intro_request.connection_first_name,
            connection_last_name=warm_intro_request.connection_last_name,
            connection_linkedin_url=warm_intro_request.connection_linkedin_url,
            connection_email=warm_intro_request.connection_email,
            status=warm_intro_request.status,
            created_at=warm_intro_request.created_at.isoformat(),
            updated_at=warm_intro_request.updated_at.isoformat(),
            user_id=str(warm_intro_request.user_id),
            connected_date=warm_intro_request.connected_date.isoformat() if warm_intro_request.connected_date else None,
            declined_date=warm_intro_request.declined_date.isoformat() if warm_intro_request.declined_date else None,
            outcome=warm_intro_request.outcome,
            outcome_date=warm_intro_request.outcome_date.isoformat() if warm_intro_request.outcome_date else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create warm intro request: {str(e)}"
        )

@router.get("/warm-intro-requests/", response_model=PaginatedWarmIntroRequestsResponse)
async def get_warm_intro_requests(
    current_user = Depends(get_current_user),
    db = Depends(get_database),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status_filter: Optional[WarmIntroStatus] = Query(None, alias="status", description="Filter by status")
):
    """
    Get paginated warm intro requests.
    
    For admin users: returns all warm intro requests from all users.
    For regular users: returns only their own warm intro requests.
    """
    user_id = UUID(str(current_user.id))
    
    try:
        # For admin users, get all requests; for regular users, get only their own
        if current_user.role == UserRole.admin:
            result = await warm_intro_requests_service.get_all_warm_intro_requests(
                db=db,
                page=page,
                limit=limit,
                status_filter=status_filter
            )
        else:
            result = await warm_intro_requests_service.get_warm_intro_requests(
                db=db,
                user_id=user_id,
                page=page,
                limit=limit,
                status_filter=status_filter
            )
        
        items = [
            WarmIntroRequestResponse(
                id=str(req.id),
                requester_name=req.requester_name,
                connection_name=req.connection_name,
                requester_first_name=req.requester_first_name,
                requester_last_name=req.requester_last_name,
                connection_first_name=req.connection_first_name,
                connection_last_name=req.connection_last_name,
                connection_linkedin_url=req.connection_linkedin_url,
                connection_email=req.connection_email,
                status=req.status,
                created_at=req.created_at.isoformat(),
                updated_at=req.updated_at.isoformat(),
                user_id=str(req.user_id),
                connected_date=req.connected_date.isoformat() if req.connected_date else None,
                declined_date=req.declined_date.isoformat() if req.declined_date else None,
                outcome=req.outcome,
                outcome_date=req.outcome_date.isoformat() if req.outcome_date else None
            )
            for req in result["items"]
        ]
        
        return PaginatedWarmIntroRequestsResponse(
            items=items,
            total=result["total"],
            page=result["page"],
            limit=result["limit"],
            total_pages=result["total_pages"],
            status_counts=result["status_counts"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch warm intro requests: {str(e)}"
        )

@router.get("/warm-intro-requests/{request_id}", response_model=WarmIntroRequestResponse)
async def get_warm_intro_request_by_id(
    request_id: UUID,
    current_user = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get a specific warm intro request by ID.
    
    Requires authentication. Only returns the request if it belongs to the current user.
    """
    user_id = UUID(str(current_user.id))
    
    try:
        warm_intro_request = await warm_intro_requests_service.get_warm_intro_request_by_id(
            db=db,
            request_id=request_id,
            user_id=user_id
        )
        
        if not warm_intro_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warm intro request not found"
            )
        
        # Additional security check: ensure the request belongs to the current user
        if warm_intro_request.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own warm intro requests"
            )
        
        return WarmIntroRequestResponse(
            id=str(warm_intro_request.id),
            requester_name=warm_intro_request.requester_name,
            connection_name=warm_intro_request.connection_name,
            requester_first_name=warm_intro_request.requester_first_name,
            requester_last_name=warm_intro_request.requester_last_name,
            connection_first_name=warm_intro_request.connection_first_name,
            connection_last_name=warm_intro_request.connection_last_name,
            connection_linkedin_url=warm_intro_request.connection_linkedin_url,
            connection_email=warm_intro_request.connection_email,
            status=warm_intro_request.status,
            created_at=warm_intro_request.created_at.isoformat(),
            updated_at=warm_intro_request.updated_at.isoformat(),
            user_id=str(warm_intro_request.user_id),
            connected_date=warm_intro_request.connected_date.isoformat() if warm_intro_request.connected_date else None,
            declined_date=warm_intro_request.declined_date.isoformat() if warm_intro_request.declined_date else None,
            outcome=warm_intro_request.outcome,
            outcome_date=warm_intro_request.outcome_date.isoformat() if warm_intro_request.outcome_date else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch warm intro request: {str(e)}"
        )

@router.patch("/warm-intro-requests/{request_id}/status", response_model=WarmIntroRequestResponse)
async def update_warm_intro_request_status(
    request_id: UUID,
    request: WarmIntroRequestUpdate,
    current_user = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Update the status of a warm intro request.
    
    For admin users: can update any warm intro request.
    For regular users: can only update their own warm intro requests.
    """
    user_id = UUID(str(current_user.id))
    
    try:
        # For admin users, allow updating any request
        if current_user.role == UserRole.admin:
            # Verify the request exists
            existing_request = await db.warm_intro_requests.find_one({"id": str(request_id)})
            if not existing_request:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Warm intro request not found"
                )
            
            # Update the status using admin function
            updated_request = await warm_intro_requests_service.update_warm_intro_request_status_admin(
                db=db,
                request_id=request_id,
                status=request.status,
                connected_date=request.connected_date,
                declined_date=request.declined_date,
                outcome=request.outcome,
                outcome_date=request.outcome_date
            )
        else:
            # For regular users, verify the request exists and belongs to them
            existing_request = await warm_intro_requests_service.get_warm_intro_request_by_id(
                db=db,
                request_id=request_id,
                user_id=user_id
            )
            
            if not existing_request:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Warm intro request not found"
                )
            
            # Additional security check: ensure the request belongs to the current user
            if existing_request.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only update your own warm intro requests"
                )
            
            # Update the status using regular function
            updated_request = await warm_intro_requests_service.update_warm_intro_request_status(
                db=db,
                request_id=request_id,
                status=request.status,
                user_id=user_id,
                connected_date=request.connected_date,
                declined_date=request.declined_date,
                outcome=request.outcome,
                outcome_date=request.outcome_date
            )
        
        if not updated_request:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update warm intro request status"
            )
        
        # If the status is being updated to "connected", schedule a follow-up email
        if request.status == WarmIntroStatus.connected:
            try:
                await schedule_follow_up_email(
                    db=db,
                    warm_intro_request_id=str(request_id),
                    requester_email=current_user.email,
                    requester_name=updated_request.requester_name,
                    connection_name=updated_request.connection_name,
                    facilitator_email=" ha@nextstepfwd.com",  # Default facilitator email
                    follow_up_days=14  # Default 14 days
                )
            except Exception as e:
                # Log the error but don't fail the request update
                print(f"Warning: Failed to schedule follow-up email: {str(e)}")
        
        return WarmIntroRequestResponse(
            id=str(updated_request.id),
            requester_name=updated_request.requester_name,
            connection_name=updated_request.connection_name,
            requester_first_name=updated_request.requester_first_name,
            requester_last_name=updated_request.requester_last_name,
            connection_first_name=updated_request.connection_first_name,
            connection_last_name=updated_request.connection_last_name,
            connection_linkedin_url=updated_request.connection_linkedin_url,
            connection_email=updated_request.connection_email,
            status=updated_request.status,
            created_at=updated_request.created_at.isoformat(),
            updated_at=updated_request.updated_at.isoformat(),
            user_id=str(updated_request.user_id),
            connected_date=updated_request.connected_date.isoformat() if updated_request.connected_date else None,
            declined_date=updated_request.declined_date.isoformat() if updated_request.declined_date else None,
            outcome=updated_request.outcome,
            outcome_date=updated_request.outcome_date.isoformat() if updated_request.outcome_date else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update warm intro request status: {str(e)}"
        )

@router.get("/warm-intro-requests/stats/counts")
async def get_warm_intro_request_counts(
    current_user = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get count statistics for warm intro requests by status.
    
    Requires authentication. Only returns counts for the current user's requests.
    """
    user_id = UUID(str(current_user.id))
    
    try:
        counts = await warm_intro_requests_service.get_warm_intro_request_counts(
            db=db,
            user_id=user_id
        )
        
        return {
            "total": counts.get("total", 0),
            "pending": counts.get("pending", 0),
            "connected": counts.get("connected", 0),
            "declined": counts.get("declined", 0)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch warm intro request counts: {str(e)}"
        )

@router.get("/warm-intro-requests/export/csv")
async def export_connected_requests_csv(
    current_user = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Export all connected warm intro requests as CSV.
    
    Requires authentication. Only exports requests belonging to the current user.
    """
    user_id = UUID(str(current_user.id))
    
    try:
        # Get all connected requests for the user
        result = await warm_intro_requests_service.get_warm_intro_requests(
            db=db,
            user_id=user_id,
            page=1,
            limit=1000,  # Large limit to get all connected requests
            status_filter=WarmIntroStatus.connected
        )
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Requester First Name',
            'Requester Last Name',
            'Connection First Name',
            'Connection Last Name',
            'Date of Connection'
        ])
        
        # Write data rows
        for req in result["items"]:
            # Split names if they're not already split
            requester_first = req.requester_first_name or req.requester_name.split(' ')[0] if req.requester_name else ''
            requester_last = req.requester_last_name or ' '.join(req.requester_name.split(' ')[1:]) if req.requester_name and len(req.requester_name.split(' ')) > 1 else ''
            
            connection_first = req.connection_first_name or req.connection_name.split(' ')[0] if req.connection_name else ''
            connection_last = req.connection_last_name or ' '.join(req.connection_name.split(' ')[1:]) if req.connection_name and len(req.connection_name.split(' ')) > 1 else ''
            
            connection_date = req.connected_date.strftime('%Y-%m-%d') if req.connected_date else ''
            
            writer.writerow([
                requester_first,
                requester_last,
                connection_first,
                connection_last,
                connection_date
            ])
        
        # Prepare response
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type='text/csv',
            headers={"Content-Disposition": "attachment; filename=connected_warm_intro_requests.csv"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export connected requests: {str(e)}"
        )
