from datetime import timedelta
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import get_db
from app.core.oauth import oauth
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if not user_in.password:
        raise HTTPException(status_code=400, detail="Password is required for registration")

    email = str(user_in.email).strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = User(
        email=email,
        name=user_in.name,
        password_hash=get_password_hash(user_in.password),
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error creating user")

    return user

@router.post("/login", response_model=Token)
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username.strip().lower()).first()
    if not user or not user.password_hash or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.get("/google")
async def login_google(request: Request):
    """Initiate Google OAuth flow by redirecting user to Google consent screen."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured on the server. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    return await oauth.google.authorize_redirect(request, settings.GOOGLE_REDIRECT_URI)

@router.get("/google/callback", name="auth_google_callback")
async def auth_google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback, create/link user, and redirect to frontend with JWT."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured on the server.",
        )

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        error_params = urlencode({"error": f"Google authorization failed: {str(exc)}"})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?{error_params}")

    userinfo = token.get("userinfo")
    if not userinfo:
        try:
            userinfo = await oauth.google.userinfo(token=token)
        except Exception:
            userinfo = {}

    google_id = str(userinfo.get("sub", "")).strip()
    email = str(userinfo.get("email", "")).strip().lower()
    name = str(userinfo.get("name") or userinfo.get("given_name") or (email.split("@")[0] if email else "ATLAS Traveler")).strip()

    if not email:
        error_params = urlencode({"error": "Google account did not provide an email address."})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?{error_params}")

    # 1. Find user by google_id
    user = None
    if google_id:
        user = db.query(User).filter(User.google_id == google_id).first()

    # 2. Find user by email if not found by google_id
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Link existing account with Google ID
            if google_id and not user.google_id:
                user.google_id = google_id
                db.add(user)
                db.commit()
                db.refresh(user)

    # 3. Create new user if not exists
    if not user:
        user = User(
            email=email,
            name=name,
            google_id=google_id or None,
            password_hash=None,
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            # If race condition, re-query
            user = db.query(User).filter(User.email == email).first()
            if not user:
                error_params = urlencode({"error": "Failed to create user account."})
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?{error_params}")

    # Generate JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )

    return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?token={access_token}")

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
