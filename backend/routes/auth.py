from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
import os
from requests_oauthlib import OAuth2Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.database import get_db
from backend.db.models import User, GoogleAccount
from backend.auth.security import get_password_hash, verify_password, create_access_token, get_current_user, decode_access_token
from datetime import datetime, timezone
import os
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["auth"])

# Shared secret key for both signup and login to restrict access
SECRET_KEY_APP = os.getenv("SECRET_KEY_APP", "simplii-dev-key")

if not os.getenv("SECRET_KEY_APP"):
    print("[AUTH WARNING] SECRET_KEY_APP not set in environment. Using default dev key.")

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    secret_key: str

class LoginRequest(BaseModel):
    username: str # This can be username or email
    password: str
    secret_key: str

class Token(BaseModel):
    access_token: str
    token_type: str

class WaitlistRequest(BaseModel):
    name: str # Username or Company Name
    email: EmailStr

@router.post("/waitlist")
async def request_waitlist(data: WaitlistRequest):
    try:
        from backend.utils.email_sender import send_email
        
        # Format as requested: "i would like to access the key [name]"
        # Added email contact info so the admin can reply
        message_body = f"i would like to access the key {data.name}<br><br>Contact Email: {data.email}"
        
        # Send to the specific admin email requested
        success = send_email(
            to_email="mohdaibad04@gmail.com", 
            subject=f"Key Access Request: {data.name}", 
            body=message_body
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to deliver email credential check.")
            
        print(f"[AUTH] Waitlist request sent for {data.email}")
        return {"message": "Request sent successfully"}
    except Exception as e:
        print(f"[AUTH ERROR] Waitlist failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    print(f"[AUTH] Signup attempt for: {user_data.username}")
    if user_data.secret_key != SECRET_KEY_APP:
        print(f"[AUTH ERROR] Invalid secret key provided by {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret key"
        )
    
    try:
        # Check if user already exists
        stmt = select(User).where((User.username == user_data.username) | (User.email == user_data.email))
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        print(f"[AUTH SUCCESS] Created user: {user_data.username}")
        # Create token immediately
        access_token = create_access_token(data={"sub": new_user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH ERROR] Signup failed for {user_data.username}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    print(f"[AUTH] Login attempt for: {login_data.username}")
    # Verify Secret Key first
    if login_data.secret_key != SECRET_KEY_APP:
        print(f"[AUTH ERROR] Invalid secret key in login attempt for {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret key"
        )

    try:
        # Check by username or email
        stmt = select(User).where((User.username == login_data.username) | (User.email == login_data.username))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(login_data.password, user.hashed_password):
            print(f"[AUTH ERROR] Failed login for {login_data.username}: Incorrect credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print(f"[AUTH SUCCESS] Logged in: {user.username}")
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH ERROR] Login failed for {login_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}

@router.get("/api-token")
async def get_api_token(current_user: User = Depends(get_current_user)):
    """Generate a JWT API token for Chrome extension use"""
    from backend.auth.security import create_access_token

    # Create a proper JWT token with the user's email
    token = create_access_token({"sub": current_user.email})

    return {
        "token": token,
        "user_id": current_user.id,
        "message": "Copy this token and paste it into the Chrome extension"
    }

# ==================== GOOGLE AUTH ====================

# Google OAuth Config
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # For dev
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "your-client-id")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "your-client-secret")
GOOGLE_REDIRECT_URI = "http://localhost:8001/api/auth/google/callback"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPE = [
    "https://www.googleapis.com/auth/userinfo.email", 
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly" # Requesting Gmail access
]

@router.get("/google/login")
async def google_login(request: Request, token: str = None):
    """Initiate Google OAuth login"""
    # If using token param to identify user, store it in state or cookie
    # State is better for security, but simple cookie works for demo
    
    oauth = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=GOOGLE_REDIRECT_URI, scope=GOOGLE_SCOPE)
    authorization_url, state = oauth.authorization_url(GOOGLE_AUTH_URL)
    
    response = RedirectResponse(authorization_url)
    if token:
         response.set_cookie(key="simplii_temp_token", value=token, max_age=300)
    
    return response

@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        oauth = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=GOOGLE_REDIRECT_URI)
        token = oauth.fetch_token(GOOGLE_TOKEN_URL, client_secret=GOOGLE_CLIENT_SECRET, authorization_response=str(request.url))
        
        # Get user info
        user_info = oauth.get("https://www.googleapis.com/oauth2/v2/userinfo").json()
        google_email = user_info.get("email")
        
        # Retrieve the user token from cookie to identify the user
        app_token = request.cookies.get("simplii_temp_token")
        
        if not app_token:
            # === LOGIN FLOW ===
            print(f"[GOOGLE AUTH] Login flow initiated for {google_email}")
            # 1. Check if user with this email exists
            stmt = select(User).where((User.email == google_email))
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                 # === AUTO SIGNUP ===
                 print(f"[GOOGLE AUTH] User not found. Creating new account for {google_email}")
                 
                 # Generate random password
                 import secrets
                 random_password = secrets.token_urlsafe(16)
                 hashed_pw = get_password_hash(random_password)
                 
                 # Generate username from email (ensure unique or handle simple collision)
                 base_username = google_email.split("@")[0]
                 # Simple check to ensure we don't crash if username taken (unlikely if email is unique/new, but cleanliness)
                 # For now, just use email prefix. In prod, would add retry logic.
                 
                 new_user = User(
                     username=base_username,
                     email=google_email,
                     hashed_password=hashed_pw
                 )
                 db.add(new_user)
                 await db.flush() # Get ID
                 await db.refresh(new_user)
                 user = new_user
                 print(f"[GOOGLE AUTH] Created new user: {user.username}")

            # User is now guaranteed to exist (found or created)
            # Create access token
            access_token = create_access_token(data={"sub": user.email})
            
            # Update/Link Google Account
            stmt_acc = select(GoogleAccount).where(GoogleAccount.user_id == user.id)
            res_acc = await db.execute(stmt_acc)
            google_acc = res_acc.scalar_one_or_none()
            
            if not google_acc:
                    google_acc = GoogleAccount(
                    user_id=user.id,
                    email=google_email,
                    access_token=token.get("access_token"),
                    refresh_token=token.get("refresh_token")
                )
                    # Calculate expiry
                    expires_in = token.get("expires_in")
                    if expires_in:
                        from datetime import timedelta
                        google_acc.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    db.add(google_acc)
            else:
                # Update tokens for existing link
                google_acc.access_token = token.get("access_token")
                # Refresh token might not always be sent on subsequent logins, only update if present
                if token.get("refresh_token"):
                    google_acc.refresh_token = token.get("refresh_token")
                
            await db.commit()
            
            # Redirect to login page which will save token and redirect to dashboard
            return RedirectResponse(url=f"/login.html?status=gmail_connected&token={access_token}")

        # === LINKING FLOW (Existing Logic for logged-in users) ===
        # Decode token to get user email/id
        payload = decode_access_token(app_token)
        if not payload or not payload.get("sub"):
            print("[GOOGLE AUTH ERROR] Invalid user token")
            return RedirectResponse(url="/?status=gmail_failed")
            
        user_email = payload.get("sub")
        
        # Find the user
        stmt = select(User).where(User.email == user_email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"[GOOGLE AUTH ERROR] User not found for email {user_email}")
            return RedirectResponse(url="/?status=gmail_failed")

        # Check if GoogleAccount exists
        stmt = select(GoogleAccount).where(GoogleAccount.user_id == user.id)
        result = await db.execute(stmt)
        google_account = result.scalar_one_or_none()
        
        if google_account:
            # Update existing
            google_account.email = google_email
            google_account.access_token = token.get("access_token")
            google_account.refresh_token = token.get("refresh_token")
            # Calculate expiry
            expires_in = token.get("expires_in")
            if expires_in:
                 from datetime import timedelta
                 google_account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            print(f"[GOOGLE AUTH] Updated Google Account for user {user.username}")
        else:
            # Create new
            google_account = GoogleAccount(
                user_id=user.id,
                email=google_email,
                access_token=token.get("access_token"),
                refresh_token=token.get("refresh_token")
            )
            # Calculate expiry
            expires_in = token.get("expires_in")
            if expires_in:
                 from datetime import timedelta
                 google_account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            db.add(google_account)
            print(f"[GOOGLE AUTH] Linked new Google Account for user {user.username}")
            
        await db.commit()
        
        # Redirect back to app settings (or show success page)
        return RedirectResponse(url="/?status=gmail_connected")
        
    except Exception as e:
        print(f"[GOOGLE AUTH ERROR] {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/?status=gmail_failed")

# ==================== MICROSOFT AUTH ====================

# Microsoft OAuth Config
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "your-microsoft-client-id")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "your-microsoft-client-secret")
MICROSOFT_REDIRECT_URI = "http://127.0.0.1:8001/api/auth/microsoft/callback"
MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_SCOPE = ["User.Read", "Mail.Read"]

@router.get("/microsoft/login")
async def microsoft_login(request: Request, token: str = None):
    """Initiate Microsoft OAuth login"""
    oauth = OAuth2Session(MICROSOFT_CLIENT_ID, redirect_uri=MICROSOFT_REDIRECT_URI, scope=MICROSOFT_SCOPE)
    authorization_url, state = oauth.authorization_url(MICROSOFT_AUTH_URL)
    
    response = RedirectResponse(authorization_url)
    if token:
         response.set_cookie(key="simplii_temp_token", value=token, max_age=300)
    
    return response

@router.get("/microsoft/callback")
async def microsoft_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Microsoft OAuth callback"""
    try:
        oauth = OAuth2Session(MICROSOFT_CLIENT_ID, redirect_uri=MICROSOFT_REDIRECT_URI, scope=MICROSOFT_SCOPE)
        token = oauth.fetch_token(MICROSOFT_TOKEN_URL, client_secret=MICROSOFT_CLIENT_SECRET, authorization_response=str(request.url))
        
        # Get user info
        user_info = oauth.get("https://graph.microsoft.com/v1.0/me").json()
        ms_email = user_info.get("mail") or user_info.get("userPrincipalName")
        
        # Retrieve the user token from cookie to identify the user
        app_token = request.cookies.get("simplii_temp_token")
        
        if not app_token:
            # === LOGIN FLOW ===
            print(f"[MICROSOFT AUTH] Login flow initiated for {ms_email}")
            # 1. Check if user with this email exists
            stmt = select(User).where((User.email == ms_email))
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                 # === AUTO SIGNUP ===
                 print(f"[MICROSOFT AUTH] User not found. Creating new account for {ms_email}")
                 
                 import secrets
                 random_password = secrets.token_urlsafe(16)
                 hashed_pw = get_password_hash(random_password)
                 
                 base_username = ms_email.split("@")[0]
                 
                 new_user = User(
                     username=base_username,
                     email=ms_email,
                     hashed_password=hashed_pw
                 )
                 db.add(new_user)
                 await db.flush()
                 await db.refresh(new_user)
                 user = new_user
                 print(f"[MICROSOFT AUTH] Created new user: {user.username}")

            # User is now guaranteed to exist
            access_token = create_access_token(data={"sub": user.email})
            
            # Update/Link Microsoft Account
            from backend.db.models import MicrosoftAccount
            stmt_acc = select(MicrosoftAccount).where(MicrosoftAccount.user_id == user.id)
            res_acc = await db.execute(stmt_acc)
            ms_acc = res_acc.scalar_one_or_none()
            
            if not ms_acc:
                    ms_acc = MicrosoftAccount(
                    user_id=user.id,
                    email=ms_email,
                    access_token=token.get("access_token"),
                    refresh_token=token.get("refresh_token")
                )
                    expires_in = token.get("expires_in")
                    if expires_in:
                        from datetime import timedelta
                        ms_acc.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    db.add(ms_acc)
            else:
                ms_acc.access_token = token.get("access_token")
                if token.get("refresh_token"):
                    ms_acc.refresh_token = token.get("refresh_token")
                
            await db.commit()
            
            return RedirectResponse(url=f"/login.html?status=microsoft_connected&token={access_token}")

        # === LINKING FLOW ===
        payload = decode_access_token(app_token)
        if not payload or not payload.get("sub"):
            print("[MICROSOFT AUTH ERROR] Invalid user token")
            return RedirectResponse(url="/?status=microsoft_failed")
            
        user_email = payload.get("sub")
        
        stmt = select(User).where(User.email == user_email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"[MICROSOFT AUTH ERROR] User not found for email {user_email}")
            return RedirectResponse(url="/?status=microsoft_failed")

        from backend.db.models import MicrosoftAccount
        stmt = select(MicrosoftAccount).where(MicrosoftAccount.user_id == user.id)
        result = await db.execute(stmt)
        ms_account = result.scalar_one_or_none()
        
        if ms_account:
            ms_account.email = ms_email
            ms_account.access_token = token.get("access_token")
            ms_account.refresh_token = token.get("refresh_token")
            expires_in = token.get("expires_in")
            if expires_in:
                 from datetime import timedelta
                 ms_account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            print(f"[MICROSOFT AUTH] Updated Microsoft Account for user {user.username}")
        else:
            ms_account = MicrosoftAccount(
                user_id=user.id,
                email=ms_email,
                access_token=token.get("access_token"),
                refresh_token=token.get("refresh_token")
            )
            expires_in = token.get("expires_in")
            if expires_in:
                 from datetime import timedelta
                 ms_account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            db.add(ms_account)
            print(f"[MICROSOFT AUTH] Linked new Microsoft Account for user {user.username}")
            
        await db.commit()
        
        return RedirectResponse(url="/?status=microsoft_connected")
        
    except Exception as e:
        print(f"[MICROSOFT AUTH ERROR] {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/?status=microsoft_failed")
