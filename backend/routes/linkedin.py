from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from backend.db.database import get_db
from backend.db.models import User, LinkedInAccount
from backend.auth.security import get_current_user, encrypt_token, decrypt_token
from backend.config import Config
import requests
from datetime import datetime, timedelta, timezone
import urllib.parse

router = APIRouter(prefix="/linkedin", tags=["linkedin"])

LINKEDIN_AUTH_BASE_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

def get_dynamic_redirect_uri(request: Request):
    """
    Dynamically determines the redirect URI based on the request host.
    This allows the same backend to work locally and in production.
    """
    host = request.headers.get("host", "")
    
    # If we are on localhost, use the localhost callback
    if "localhost" in host or "127.0.0.1" in host:
        return "http://localhost:8000/api/linkedin/callback"
    
    # Default to production URL if not on localhost
    # You can also use Config.LINKEDIN_REDIRECT_URI as the primary source
    prod_uri = Config.LINKEDIN_REDIRECT_URI or "https://postflow.panscience.ai/api/linkedin/callback"
    return prod_uri

@router.get("/auth-url")
async def get_auth_url(request: Request, user: User = Depends(get_current_user)):
    # Standardize redirect URI - LinkedIn is extremely strict.
    redirect_uri = get_dynamic_redirect_uri(request)
    
    print(f"[DEBUG] Initiating LinkedIn OAuth with Redirect URI: {redirect_uri}")
    
    params = {
        "response_type": "code",
        "client_id": Config.LINKEDIN_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email w_member_social",
    }
    url = f"{LINKEDIN_AUTH_BASE_URL}?{urllib.parse.urlencode(params)}"
    return {"url": url}

@router.get("/callback")
async def linkedin_callback(request: Request, code: str):
    """
    LinkedIn redirects here. We redirect to the frontend root with the code
    so the frontend can handle the connection while authenticated.
    """
    print(f"[DEBUG] LinkedIn Callback received with code: {code[:10]}...")
    
    # Use relative redirect to stay on the same domain (local or prod)
    return RedirectResponse(url=f"/?code={code}")

@router.post("/connect")
async def connect_linkedin(request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    data = await request.json()
    code = data.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Code is required")

    redirect_uri = get_dynamic_redirect_uri(request)
    print(f"[DEBUG] Exchanging code for token with Redirect URI: {redirect_uri}")

    # Exchange code for token
    token_resp = requests.post(
        LINKEDIN_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": Config.LINKEDIN_CLIENT_ID,
            "client_secret": Config.LINKEDIN_CLIENT_SECRET,
        },
    )
    
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to get token: {token_resp.text}")
    
    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in")
    
    # Get user info
    user_info_resp = requests.get(
        LINKEDIN_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    if user_info_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    
    user_info = user_info_resp.json()
    linkedin_urn = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")
    
    if not linkedin_urn:
        raise HTTPException(status_code=400, detail="LinkedIn URN not found in user info")

    # Encrypt token
    encrypted_token = encrypt_token(access_token)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in) if expires_in else None

    # Check if this LinkedIn account already exists for THIS user
    stmt = select(LinkedInAccount).where(
        LinkedInAccount.simplii_user_id == user.id,
        LinkedInAccount.linkedin_person_urn == linkedin_urn
    )
    result = await db.execute(stmt)
    existing_account = result.scalar_one_or_none()

    if existing_account:
        existing_account.access_token = encrypted_token
        existing_account.token_expires_at = expires_at
        existing_account.linkedin_email = email
        existing_account.display_name = name
    else:
        new_account = LinkedInAccount(
            simplii_user_id=user.id,
            linkedin_person_urn=linkedin_urn,
            linkedin_email=email,
            display_name=name,
            access_token=encrypted_token,
            token_expires_at=expires_at
        )
        db.add(new_account)

    await db.commit()
    return {"status": "success", "message": "LinkedIn account connected"}

@router.get("/accounts")
async def get_accounts(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(LinkedInAccount).where(LinkedInAccount.simplii_user_id == user.id)
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    
    return [
        {
            "id": acc.id,
            "display_name": acc.display_name,
            "linkedin_email": acc.linkedin_email,
            "status": "active" if acc.token_expires_at > datetime.now(timezone.utc) else "expired",
            "expires_at": acc.token_expires_at
        }
        for acc in accounts
    ]

@router.delete("/accounts/{account_id}")
async def disconnect_account(account_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = delete(LinkedInAccount).where(
        LinkedInAccount.id == account_id,
        LinkedInAccount.simplii_user_id == user.id
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "success", "message": "Account disconnected"}
