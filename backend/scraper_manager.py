"""Scraper execution manager with background threading and monitoring."""

import threading
import logging
import json
import sys
import os
from datetime import datetime
from typing import Optional, Dict, List, Callable
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from .database import (
    create_scraper_run,
    update_scraper_run,
    get_current_scraper_run,
    log_audit
)

logger = logging.getLogger(__name__)


class LogCapture:
    """Capture stdout/stderr to a list of log lines."""

    def __init__(self):
        self.lines: List[str] = []
        self.lock = threading.Lock()

    def write(self, message: str):
        """Write a message to the log."""
        if message.strip():
            with self.lock:
                self.lines.append(message.rstrip('\n'))

    def flush(self):
        """Flush (no-op)."""
        pass

    def get_logs(self) -> str:
        """Get all logs as a single string."""
        with self.lock:
            return '\n'.join(self.lines)


class ScraperManager:
    """Manages scraper execution and monitoring."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.current_run_id: Optional[int] = None
        self.current_thread: Optional[threading.Thread] = None
        self.log_capture: Optional[LogCapture] = None
        self.cancel_flag = False
        self.lock = threading.Lock()
        self.subscribers: List[Callable] = []

    def is_running(self) -> bool:
        """Check if scraper is currently running."""
        with self.lock:
            return self.current_thread is not None and self.current_thread.is_alive()

    def get_current_run_id(self) -> Optional[int]:
        """Get the ID of the currently running scraper run."""
        with self.lock:
            return self.current_run_id

    def subscribe(self, callback: Callable):
        """Subscribe to scraper updates."""
        with self.lock:
            self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """Unsubscribe from scraper updates."""
        with self.lock:
            if callback in self.subscribers:
                self.subscribers.remove(callback)

    def _notify_subscribers(self, message: Dict):
        """Notify all subscribers of an update."""
        with self.lock:
            subscribers = self.subscribers.copy()

        for callback in subscribers:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")

    def trigger_scrape(
        self,
        limit: int = 100,
        story_types: Optional[List[str]] = None,
        username: str = "system"
    ) -> int:
        """
        Trigger a scraper run and return the run ID.

        Args:
            limit: Number of stories to fetch per type
            story_types: List of story types to fetch
            username: Admin username who triggered the scrape

        Returns:
            The scraper run ID
        """
        if self.is_running():
            raise RuntimeError("Scraper is already running")

        # Default story types
        if story_types is None:
            story_types = ["topstories", "newstories", "showstories", "askstories", "jobstories"]

        # Create run record
        config = {
            "limit": limit,
            "story_types": story_types,
            "force_ipv4": os.environ.get("SUPABASE_FORCE_IPV4", "1") == "1"
        }

        try:
            run_id = create_scraper_run("manual", username, config)
        except Exception as e:
            logger.error(f"Error creating scraper run: {e}")
            raise

        # Start background thread
        with self.lock:
            self.current_run_id = run_id
            self.cancel_flag = False
            self.log_capture = LogCapture()
            self.current_thread = threading.Thread(
                target=self._run_scraper,
                args=(run_id, limit, story_types),
                daemon=False
            )
            self.current_thread.start()

        logger.info(f"Scraper run {run_id} started (limit={limit})")
        self._notify_subscribers({
            "type": "status",
            "run_id": run_id,
            "status": "running"
        })

        return run_id

    def _run_scraper(self, run_id: int, limit: int, story_types: List[str]):
        """Execute scraper in a thread."""
        start_time = datetime.utcnow()

        try:
            # Set environment variables for scraper
            os.environ["HN_LIMIT"] = str(limit)
            os.environ["SUPABASE_DB_URL"] = self.db_url

            # Capture output
            log_capture = self.log_capture
            stories_processed = 0
            errors = 0

            # Import and run scraper
            try:
                # Add parent directory to path to import scrape_hn
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)

                from scrape_hn import main as scrape_main

                # Redirect stdout/stderr
                with redirect_stdout(log_capture), redirect_stderr(log_capture):
                    # Add logging handler
                    handler = logging.StreamHandler(log_capture)
                    handler.setFormatter(logging.Formatter(
                        '%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S'
                    ))
                    scraper_logger = logging.getLogger('scrape_hn')
                    scraper_logger.addHandler(handler)

                    # Run scraper
                    scrape_main()

            except ImportError as e:
                error_msg = f"ERROR: Could not import scrape_hn module: {str(e)}"
                log_capture.write(error_msg)
                logger.error(error_msg, exc_info=True)
                errors += 1
            except Exception as e:
                error_msg = f"ERROR: Scraper failed: {str(e)}"
                log_capture.write(error_msg)
                logger.error(f"Scraper error: {e}", exc_info=True)
                errors += 1

            # Get logs
            logs = log_capture.get_logs()

            # Parse log output to count stories (simple regex)
            import re
            story_matches = re.findall(r'Processing story (\d+)', logs)
            stories_processed = len(story_matches)

            # Update run record
            update_scraper_run(
                run_id,
                status="completed",
                stories_processed=stories_processed,
                errors_count=errors,
                logs=logs,
                error_message=None
            )

            logger.info(f"Scraper run {run_id} completed: {stories_processed} stories")
            self._notify_subscribers({
                "type": "status",
                "run_id": run_id,
                "status": "completed",
                "stories_processed": stories_processed,
                "errors_count": errors
            })

        except Exception as e:
            logger.error(f"Scraper thread error: {e}", exc_info=True)

            # Update run record with error
            logs = log_capture.get_logs() if log_capture else str(e)
            update_scraper_run(
                run_id,
                status="failed",
                logs=logs,
                error_message=str(e)
            )

            self._notify_subscribers({
                "type": "status",
                "run_id": run_id,
                "status": "failed",
                "error_message": str(e)
            })

        finally:
            # Clean up
            with self.lock:
                self.current_run_id = None
                self.current_thread = None
                self.log_capture = None

    def cancel_scrape(self) -> bool:
        """
        Request cancellation of the current scraper run.

        Returns:
            True if cancellation was requested, False if no scraper running
        """
        if not self.is_running():
            return False

        with self.lock:
            self.cancel_flag = True

        run_id = self.get_current_run_id()
        logger.info(f"Scraper run {run_id} cancellation requested")

        self._notify_subscribers({
            "type": "status",
            "run_id": run_id,
            "status": "cancelled"
        })

        return True

    def wait_for_completion(self, timeout: float = None) -> bool:
        """
        Wait for current scraper run to complete.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if completed, False if timeout
        """
        if self.current_thread is None:
            return True

        self.current_thread.join(timeout=timeout)
        return not self.current_thread.is_alive()


# Global scraper manager instance
_scraper_manager: Optional[ScraperManager] = None


def get_scraper_manager(db_url: str) -> ScraperManager:
    """Get or create the global scraper manager."""
    global _scraper_manager

    if _scraper_manager is None:
        _scraper_manager = ScraperManager(db_url)

    return _scraper_manager
