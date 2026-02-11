"""Database connection and utilities."""

import os
import socket
import psycopg2
import psycopg2.extras
from urllib.parse import unquote, urlparse
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_db_url() -> str:
    """Get database URL from environment."""
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("Missing SUPABASE_DB_URL environment variable")
    return db_url


def get_connection():
    """Create a database connection with retry logic and IPv4 preference."""
    db_url = get_db_url()
    parsed = urlparse(db_url)

    # Try to resolve hostname to IPv4 if enabled
    hostaddr = None
    if os.environ.get("SUPABASE_FORCE_IPV4", "1") == "1" and parsed.hostname:
        try:
            hostaddr = socket.gethostbyname(parsed.hostname)
        except socket.gaierror:
            logger.warning(f"Could not resolve {parsed.hostname} to IPv4, using hostname")
            hostaddr = None

    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    dbname = (parsed.path or "").lstrip("/") or "postgres"
    port = parsed.port or 5432
    host = hostaddr or (parsed.hostname or "")

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        hostaddr=hostaddr if hostaddr else None,
        port=port,
        sslmode="require",
        connect_timeout=15,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )


def execute_query(query: str, params: tuple = None, fetch: bool = False, fetch_all: bool = True):
    """Execute a query and optionally fetch results."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or ())
            if fetch:
                return cur.fetchall() if fetch_all else cur.fetchone()
            else:
                conn.commit()
                return None
    finally:
        conn.close()


def execute_insert(query: str, params: tuple) -> int:
    """Execute an INSERT and return the last inserted ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if "RETURNING" in query.upper():
                result = cur.fetchone()
                conn.commit()
                return result[0] if result else None
            else:
                conn.commit()
                return None
    finally:
        conn.close()


def execute_update(query: str, params: tuple) -> int:
    """Execute an UPDATE and return rows affected."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            affected = cur.rowcount
            conn.commit()
            return affected
    finally:
        conn.close()


def execute_delete(query: str, params: tuple) -> int:
    """Execute a DELETE and return rows affected."""
    return execute_update(query, params)


def get_admin_user_by_username(username: str) -> Optional[dict]:
    """Get admin user by username."""
    result = execute_query(
        "SELECT id, username, password_hash, email, created_at, last_login FROM admin_users WHERE username = %s",
        (username,),
        fetch=True,
        fetch_all=False
    )
    return result


def get_admin_user_by_id(user_id: int) -> Optional[dict]:
    """Get admin user by ID."""
    result = execute_query(
        "SELECT id, username, email, created_at, last_login FROM admin_users WHERE id = %s",
        (user_id,),
        fetch=True,
        fetch_all=False
    )
    return result


def create_admin_user(username: str, password_hash: str, email: Optional[str] = None) -> int:
    """Create a new admin user and return the ID."""
    return execute_insert(
        "INSERT INTO admin_users (username, password_hash, email) VALUES (%s, %s, %s) RETURNING id",
        (username, password_hash, email)
    )


def update_admin_last_login(user_id: int) -> None:
    """Update admin user's last_login timestamp."""
    execute_update(
        "UPDATE admin_users SET last_login = now() WHERE id = %s",
        (user_id,)
    )


def create_scraper_run(
    trigger_type: str,
    triggered_by: Optional[str],
    config: dict
) -> int:
    """Create a new scraper run record and return the ID."""
    import json
    return execute_insert(
        "INSERT INTO scraper_runs (started_at, status, trigger_type, triggered_by, config) VALUES (now(), 'running', %s, %s, %s) RETURNING id",
        (trigger_type, triggered_by, json.dumps(config))
    )


def update_scraper_run(
    run_id: int,
    status: str,
    stories_processed: int = 0,
    errors_count: int = 0,
    logs: Optional[str] = None,
    error_message: Optional[str] = None
) -> None:
    """Update a scraper run record."""
    execute_update(
        """UPDATE scraper_runs
        SET status = %s, completed_at = now(), stories_processed = %s,
            errors_count = %s, logs = %s, error_message = %s
        WHERE id = %s""",
        (status, stories_processed, errors_count, logs, error_message, run_id)
    )


def get_scraper_run(run_id: int) -> Optional[dict]:
    """Get a scraper run by ID."""
    result = execute_query(
        """SELECT id, started_at, completed_at, status, trigger_type, triggered_by,
                  stories_processed, errors_count, config, logs, error_message
           FROM scraper_runs WHERE id = %s""",
        (run_id,),
        fetch=True,
        fetch_all=False
    )
    return result


def get_scraper_runs(limit: int = 20, offset: int = 0) -> tuple:
    """Get paginated list of scraper runs."""
    runs = execute_query(
        """SELECT id, started_at, completed_at, status, trigger_type, triggered_by,
                  stories_processed, errors_count, config, logs, error_message
           FROM scraper_runs
           ORDER BY started_at DESC
           LIMIT %s OFFSET %s""",
        (limit, offset),
        fetch=True,
        fetch_all=True
    )

    count_result = execute_query(
        "SELECT COUNT(*) as count FROM scraper_runs",
        fetch=True,
        fetch_all=False
    )

    return runs or [], count_result['count'] if count_result else 0


def get_current_scraper_run() -> Optional[dict]:
    """Get the currently running scraper run."""
    result = execute_query(
        """SELECT id, started_at, completed_at, status, trigger_type, triggered_by,
                  stories_processed, errors_count, config, logs, error_message
           FROM scraper_runs
           WHERE status = 'running'
           LIMIT 1""",
        fetch=True,
        fetch_all=False
    )
    return result


def get_config_value(key: str) -> Optional[dict]:
    """Get a configuration value."""
    result = execute_query(
        "SELECT key, value, updated_at, updated_by FROM system_config WHERE key = %s",
        (key,),
        fetch=True,
        fetch_all=False
    )
    return result


def get_all_config() -> list:
    """Get all configuration values."""
    results = execute_query(
        "SELECT key, value, updated_at, updated_by FROM system_config ORDER BY key",
        fetch=True,
        fetch_all=True
    )
    return results or []


def set_config_value(key: str, value: dict, updated_by: str) -> None:
    """Set or update a configuration value."""
    import json
    execute_update(
        """INSERT INTO system_config (key, value, updated_by)
           VALUES (%s, %s, %s)
           ON CONFLICT (key) DO UPDATE SET value = %s, updated_by = %s, updated_at = now()""",
        (key, json.dumps(value), updated_by, json.dumps(value), updated_by)
    )


def log_audit(username: str, action: str, entity_type: Optional[str] = None,
              entity_id: Optional[int] = None, old_value: Optional[dict] = None,
              new_value: Optional[dict] = None) -> None:
    """Log an audit action."""
    import json
    execute_insert(
        """INSERT INTO audit_log (timestamp, username, action, entity_type, entity_id, old_value, new_value)
           VALUES (now(), %s, %s, %s, %s, %s, %s)""",
        (username, action, entity_type, entity_id,
         json.dumps(old_value) if old_value else None,
         json.dumps(new_value) if new_value else None)
    )
