"""Authentication logic for admin dashboard."""

import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from passlib.context import CryptContext
from .database import (
    get_admin_user_by_username,
    get_admin_user_by_id,
    create_admin_user,
    update_admin_last_login
)

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory session store (format: {session_id: {user_id, expires_at}})
_sessions: Dict[str, dict] = {}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_session(user_id: int) -> str:
    """Create a new session and return the session ID."""
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    _sessions[session_id] = {
        'user_id': user_id,
        'expires_at': expires_at
    }
    return session_id


def get_session_user_id(session_id: str) -> Optional[int]:
    """Get the user ID from a session, or None if invalid/expired."""
    if session_id not in _sessions:
        return None

    session = _sessions[session_id]

    # Check expiration
    if datetime.utcnow() > session['expires_at']:
        del _sessions[session_id]
        return None

    # Renew session expiration
    session['expires_at'] = datetime.utcnow() + timedelta(hours=24)
    return session['user_id']


def delete_session(session_id: str) -> None:
    """Delete a session."""
    if session_id in _sessions:
        del _sessions[session_id]


def authenticate_user(username: str, password: str) -> Optional[int]:
    """Authenticate a user and return their ID, or None if authentication fails."""
    user = get_admin_user_by_username(username)

    if not user:
        logger.warning(f"Login attempt for non-existent user: {username}")
        return None

    if not verify_password(password, user['password_hash']):
        logger.warning(f"Failed password for user: {username}")
        return None

    # Update last login
    try:
        update_admin_last_login(user['id'])
    except Exception as e:
        logger.error(f"Error updating last login: {e}")

    logger.info(f"User authenticated: {username}")
    return user['id']


def create_admin(username: str, password: str, email: Optional[str] = None) -> int:
    """Create a new admin user and return their ID."""
    # Check if user already exists
    existing = get_admin_user_by_username(username)
    if existing:
        raise ValueError(f"User '{username}' already exists")

    password_hash = hash_password(password)
    user_id = create_admin_user(username, password_hash, email)

    logger.info(f"Created new admin user: {username}")
    return user_id


def get_current_user(session_id: str) -> Optional[dict]:
    """Get the current user info from a session."""
    user_id = get_session_user_id(session_id)
    if not user_id:
        return None

    return get_admin_user_by_id(user_id)
