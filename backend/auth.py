import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, AuthToken

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a unique salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored salt$hash."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 2:
            return False
        salt_hex, key_hex = parts
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False

def create_access_token(db: Session, user_id: int, days: int = 7) -> str:
    """Generate a secure session token and persist to database."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=days)

    auth_token = AuthToken(
        token=token,
        user_id=user_id,
        created_at=now,
        expires_at=expires_at
    )
    db.add(auth_token)
    db.commit()
    return token

def revoke_token(db: Session, token: str) -> bool:
    """Revoke a token upon logout."""
    token_obj = db.query(AuthToken).filter(AuthToken.token == token).first()
    if token_obj:
        db.delete(token_obj)
        db.commit()
        return True
    return False

def get_token_from_header(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    parts = auth_header.split(" ")
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI dependency to retrieve the authenticated user."""
    token = get_token_from_header(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc)
    token_record = (
        db.query(AuthToken)
        .filter(AuthToken.token == token, AuthToken.expires_at > now)
        .first()
    )

    if not token_record or not token_record.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_record.user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency requiring admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: Administrator rights required."
        )
    return current_user
