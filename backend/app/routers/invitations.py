from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime, timedelta

from app.models.invitation import InvitationCreate, InvitationPublic, InvitationUpdate
from app.models.user import UserRole
from app.core.db import get_database
from app.services import invitation_service, auth_service

router = APIRouter()

async def get_current_admin_user(current_user: dict = Depends(auth_service.get_current_user)):
    """Dependency to ensure only admin users can access admin endpoints"""
    if current_user.get("role") != UserRole.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@router.post("/invitations", response_model=InvitationPublic, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    invitation_data: dict,
    current_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Create a new invitation (Admin only)"""
    # Set expiration to 7 days from now if not provided
    expires_at = invitation_data.get("expires_at")
    if not expires_at:
        expires_at = datetime.utcnow() + timedelta(days=7)
    
    invitation = InvitationCreate(
        email=invitation_data["email"],
        invited_by=current_user["email"],
        message=invitation_data.get("message"),
        expires_at=expires_at
    )
    
    new_invitation = await invitation_service.create_invitation(db, invitation, current_user["email"])
    return new_invitation

@router.get("/invitations", response_model=List[InvitationPublic])
async def get_invitations(
    current_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Get all invitations sent by the current admin user"""
    invitations = await invitation_service.get_invitations_by_inviter(db, current_user["email"])
    return invitations

@router.get("/invitations/validate/{invitation_code}")
async def validate_invitation(invitation_code: str, db=Depends(get_database)):
    """Validate an invitation code (public endpoint for registration)"""
    invitation = await invitation_service.get_invitation_by_code(db, invitation_code)
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation code"
        )
    
    if invitation["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is no longer valid"
        )
    
    if invitation["expires_at"] < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    return {
        "valid": True,
        "email": invitation["email"],
        "invited_by": invitation["invited_by"],
        "message": invitation.get("message"),
        "expires_at": invitation["expires_at"]
    }

@router.put("/invitations/{invitation_id}", response_model=InvitationPublic)
async def update_invitation(
    invitation_id: str,
    update: InvitationUpdate,
    current_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Update an invitation (Admin only)"""
    updated_invitation = await invitation_service.update_invitation(db, invitation_id, update)
    return updated_invitation

@router.delete("/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Revoke an invitation (Admin only)"""
    await invitation_service.revoke_invitation(db, invitation_id)
    return {"message": "Invitation revoked successfully"}

@router.post("/invitations/cleanup")
async def cleanup_expired_invitations(
    current_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Clean up expired invitations (Admin only)"""
    await invitation_service.cleanup_expired_invitations(db)
    return {"message": "Expired invitations cleaned up successfully"}