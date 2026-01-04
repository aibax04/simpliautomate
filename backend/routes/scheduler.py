from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from backend.db.database import get_db, AsyncSessionLocal
from backend.db.models import User, ScheduledPost, LinkedInAccount
from backend.auth.security import get_current_user
from backend.utils.email_sender import send_email
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

class ScheduleRequest(BaseModel):
    linkedin_account_id: int
    content: str
    image_url: Optional[str] = None
    scheduled_at: datetime
    notification_email: Optional[str] = None

class TestEmailRequest(BaseModel):
    email: str

@router.post("/schedule")
async def schedule_post(
    request: ScheduleRequest, 
    db: AsyncSession = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    # Verify account ownership
    stmt = select(LinkedInAccount).where(
        LinkedInAccount.id == request.linkedin_account_id,
        LinkedInAccount.simplii_user_id == user.id
    )
    res = await db.execute(stmt)
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="LinkedIn account not found")

    new_post = ScheduledPost(
        user_id=user.id,
        linkedin_account_id=request.linkedin_account_id,
        content=request.content,
        image_url=request.image_url,
        scheduled_at=request.scheduled_at,
        notification_email=request.notification_email,
        status="pending"
    )
    db.add(new_post)
    await db.commit()
    return {"status": "success", "message": "Post scheduled successfully"}

@router.get("/scheduled-posts")
async def get_scheduled_posts(
    db: AsyncSession = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    stmt = select(ScheduledPost, LinkedInAccount).join(
        LinkedInAccount, ScheduledPost.linkedin_account_id == LinkedInAccount.id
    ).where(
        ScheduledPost.user_id == user.id
    ).order_by(ScheduledPost.scheduled_at.asc())
    
    res = await db.execute(stmt)
    results = []
    for post, account in res.all():
        results.append({
            "id": post.id,
            "content": post.content[:100] + "...",
            "image_url": post.image_url,
            "scheduled_at": post.scheduled_at,
            "status": post.status,
            "account_name": account.display_name,
            "error_message": post.error_message
        })
    return results

@router.delete("/scheduled-posts/{post_id}")
async def cancel_scheduled_post(
    post_id: int, 
    db: AsyncSession = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    stmt = delete(ScheduledPost).where(
        ScheduledPost.id == post_id,
        ScheduledPost.user_id == user.id
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "success", "message": "Scheduled post cancelled"}

@router.post("/test-email")
async def test_email(request: TestEmailRequest, user: User = Depends(get_current_user)):
    success = send_email(
        to_email=request.email,
        subject="Simplii Test Email",
        body=f"<h1>Hello {user.username}!</h1><p>This is a test email to confirm your Simplii email notifications are working correctly.</p>"
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send test email. Check your SMTP settings.")
    return {"status": "success", "message": f"Test email sent to {request.email}"}
