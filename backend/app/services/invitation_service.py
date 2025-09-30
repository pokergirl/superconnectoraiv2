from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import List, Optional
import secrets
import string
from app.models.invitation import InvitationCreate, InvitationInDB, InvitationStatus, InvitationUpdate
from app.core.db import get_database

def generate_invitation_code(length: int = 32) -> str:
    """Generate a secure random invitation code"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

async def create_invitation(db, invitation: InvitationCreate, invited_by_email: str) -> dict:
    """Create a new invitation"""
    # Check if invitation already exists for this email
    existing = await db.invitations.find_one({
        "email": invitation.email,
        "status": {"$in": [InvitationStatus.pending.value]}
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active invitation already exists for this email"
        )
    
    # Create invitation with generated code
    invitation_code = generate_invitation_code()
    invitation_in_db = InvitationInDB(
        **invitation.model_dump()
    )
    
    # Convert to dict for MongoDB
    invitation_dict = invitation_in_db.model_dump()
    invitation_dict["id"] = str(invitation_dict["id"])
    invitation_dict["invitation_code"] = invitation_code
    
    await db.invitations.insert_one(invitation_dict)
    return invitation_dict

async def get_invitation_by_code(db, invitation_code: str) -> Optional[dict]:
    """Get invitation by invitation code"""
    return await db.invitations.find_one({"invitation_code": invitation_code})

async def get_invitation_by_email(db, email: str) -> Optional[dict]:
    """Get active invitation by email"""
    return await db.invitations.find_one({
        "email": email,
        "status": InvitationStatus.pending.value,
        "expires_at": {"$gt": datetime.utcnow()}
    })

async def get_invitations_by_inviter(db, invited_by_email: str) -> List[dict]:
    """Get all invitations sent by a specific user"""
    cursor = db.invitations.find({"invited_by": invited_by_email})
    return await cursor.to_list(length=None)

async def update_invitation(db, invitation_id: str, update: InvitationUpdate) -> dict:
    """Update invitation status"""
    update_dict = update.model_dump(exclude_unset=True)
    
    result = await db.invitations.update_one(
        {"id": invitation_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    return await db.invitations.find_one({"id": invitation_id})

async def accept_invitation(db, invitation_code: str) -> dict:
    """Accept an invitation"""
    invitation = await get_invitation_by_code(db, invitation_code)
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation code"
        )
    
    if invitation["status"] != InvitationStatus.pending.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is no longer valid"
        )
    
    if invitation["expires_at"] < datetime.utcnow():
        # Mark as expired
        await update_invitation(db, invitation["id"], InvitationUpdate(status=InvitationStatus.expired))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    # Mark as accepted
    update = InvitationUpdate(
        status=InvitationStatus.accepted,
        accepted_at=datetime.utcnow()
    )
    return await update_invitation(db, invitation["id"], update)

async def revoke_invitation(db, invitation_id: str) -> dict:
    """Revoke an invitation"""
    update = InvitationUpdate(status=InvitationStatus.revoked)
    return await update_invitation(db, invitation_id, update)

async def cleanup_expired_invitations(db):
    """Clean up expired invitations"""
    await db.invitations.update_many(
        {
            "status": InvitationStatus.pending.value,
            "expires_at": {"$lt": datetime.utcnow()}
        },
        {"$set": {"status": InvitationStatus.expired.value}}
    )

async def is_user_authorized(db, email: str) -> bool:
    """Check if a user is authorized to access the system"""
    # Check if user has an accepted invitation
    invitation = await db.invitations.find_one({
        "email": email,
        "status": InvitationStatus.accepted.value
    })
    
    if invitation:
        return True
    
    # Check if user is an admin (for bootstrap purposes)
    user = await db.users.find_one({"email": email})
    if user and user.get("role") == "admin":
        return True
    
    return False