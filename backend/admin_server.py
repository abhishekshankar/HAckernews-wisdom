"""FastAPI admin server for HackerNews Wisdom scraper."""

import os
import sys
import logging
import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Cookie, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

from .auth import authenticate_user, create_session, get_current_user, create_admin
from .database import get_connection
from .models import LoginRequest, LoginResponse, UserResponse, PublicConfigResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# Lifespan event handlers
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Admin server starting up")
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM admin_users LIMIT 1")
        conn.close()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Admin server shutting down")


# Create FastAPI app
app = FastAPI(
    title="HackerNews Wisdom Admin API",
    description="Admin API for managing the HackerNews Wisdom scraper",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (allow localhost for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get current user
def get_current_user_from_cookie(session_id: str = Cookie(None)) -> dict:
    """Get current user from session cookie."""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_current_user(session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return user


# --- Public Routes ---

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve admin dashboard HTML."""
    admin_html_path = Path(__file__).parent.parent / "frontend" / "admin-dashboard.html"
    if admin_html_path.exists():
        return FileResponse(admin_html_path)
    return "<h1>Admin Dashboard</h1><p>Frontend not found</p>"


@app.get("/admin", response_class=HTMLResponse)
async def admin():
    """Serve admin dashboard at /admin."""
    admin_html_path = Path(__file__).parent.parent / "frontend" / "admin-dashboard.html"
    if admin_html_path.exists():
        return FileResponse(admin_html_path)
    return "<h1>Admin Dashboard</h1><p>Frontend not found</p>"


@app.get("/api/public/config", response_model=PublicConfigResponse)
async def get_public_config():
    """Get public configuration (Supabase credentials for frontend)."""
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not supabase_url or not supabase_anon_key:
        raise HTTPException(
            status_code=503,
            detail="Supabase credentials not configured"
        )

    return PublicConfigResponse(
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key
    )


# --- Authentication Routes ---

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """Login and create session."""
    user_id = authenticate_user(request.username, request.password)

    if not user_id:
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    session_id = create_session(user_id)

    # Set session cookie (HttpOnly, Secure for production)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="strict",
        max_age=86400  # 24 hours
    )

    user = get_current_user(session_id)
    logger.info(f"User logged in: {request.username}")

    return LoginResponse(
        id=user['id'],
        username=user['username'],
        email=user.get('email')
    )


@app.post("/api/auth/logout")
async def logout(response: Response):
    """Logout and clear session."""
    response.delete_cookie("session_id")
    return {"success": True}


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user_from_cookie)):
    """Get current user info."""
    return UserResponse(
        id=current_user['id'],
        username=current_user['username'],
        email=current_user.get('email'),
        created_at=current_user['created_at'],
        last_login=current_user.get('last_login')
    )


# --- Health check ---

@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")


# --- CLI Commands ---

def create_admin_user(username: str, password: str, email: str = None):
    """CLI command to create an admin user."""
    try:
        user_id = create_admin(username, password, email)
        print(f"✓ Admin user created: {username} (ID: {user_id})")
        return user_id
    except ValueError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        print(f"✗ Error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="HackerNews Wisdom Admin Server")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create admin subcommand
    create_admin_parser = subparsers.add_parser("create-admin", help="Create an admin user")
    create_admin_parser.add_argument("--username", required=True, help="Admin username")
    create_admin_parser.add_argument("--password", required=True, help="Admin password")
    create_admin_parser.add_argument("--email", help="Admin email")

    args = parser.parse_args()

    if args.command == "create-admin":
        create_admin_user(args.username, args.password, args.email)
    else:
        # Default: start server
        import uvicorn

        host = os.environ.get("ADMIN_HOST", "127.0.0.1")
        port = int(os.environ.get("ADMIN_PORT", "8000"))

        logger.info(f"Starting admin server on {host}:{port}")
        logger.info("Open http://localhost:8000/admin in your browser")

        uvicorn.run(
            "backend.admin_server:app",
            host=host,
            port=port,
            reload=os.environ.get("ADMIN_RELOAD", "false").lower() == "true"
        )


if __name__ == "__main__":
    main()
