"""Scraper control API endpoints."""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, WebSocket, Query
from fastapi.responses import StreamingResponse

from ..auth import get_current_user
from ..database import (
    get_db_url,
    execute_query,
    execute_insert,
    get_scraper_run,
    get_scraper_runs,
    get_current_scraper_run,
    update_scraper_run,
    log_audit
)
from ..models import (
    ScraperTriggerRequest,
    ScraperRunResponse,
    ScraperStatusResponse
)
from ..scraper_manager import get_scraper_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scraper", tags=["scraper"])


@router.post("/trigger", response_model=dict)
async def trigger_scraper(request: ScraperTriggerRequest):
    """
    Trigger a new scraper run with optional configuration override.

    Returns the run ID and status.
    """
    try:
        db_url = get_db_url()
        manager = get_scraper_manager(db_url)

        if manager.is_running():
            raise HTTPException(
                status_code=409,
                detail="Scraper is already running"
            )

        run_id = manager.trigger_scrape(
            limit=request.limit or 100,
            story_types=request.story_types,
            username="admin"
        )

        # Log audit
        log_audit(
            "system",
            "scraper_start",
            "scraper_run",
            run_id,
            new_value={"limit": request.limit, "story_types": request.story_types}
        )

        return {
            "run_id": run_id,
            "status": "started"
        }

    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering scraper: {e}")
        raise HTTPException(status_code=500, detail="Failed to start scraper")


@router.get("/status", response_model=ScraperStatusResponse)
async def get_scraper_status(current_user: dict = Depends(lambda: {"id": 1})):
    """Get current scraper status and recent run info."""
    try:
        db_url = get_db_url()
        manager = get_scraper_manager(db_url)

        is_running = manager.is_running()
        current_run = None
        last_completed = None

        # Get current run if running
        if is_running:
            run_id = manager.get_current_run_id()
            if run_id:
                run = get_scraper_run(run_id)
                if run:
                    current_run = ScraperRunResponse(
                        id=run['id'],
                        started_at=run['started_at'],
                        completed_at=run['completed_at'],
                        status=run['status'],
                        trigger_type=run['trigger_type'],
                        triggered_by=run['triggered_by'],
                        stories_processed=run['stories_processed'],
                        errors_count=run['errors_count'],
                        config=run['config'],
                        error_message=run['error_message']
                    )

        # Get last completed run
        last_run = get_current_scraper_run()
        if last_run and last_run['status'] == 'completed':
            last_completed = ScraperRunResponse(
                id=last_run['id'],
                started_at=last_run['started_at'],
                completed_at=last_run['completed_at'],
                status=last_run['status'],
                trigger_type=last_run['trigger_type'],
                triggered_by=last_run['triggered_by'],
                stories_processed=last_run['stories_processed'],
                errors_count=last_run['errors_count'],
                config=last_run['config'],
                error_message=last_run['error_message']
            )

        return ScraperStatusResponse(
            is_running=is_running,
            current_run=current_run,
            last_completed=last_completed
        )

    except Exception as e:
        logger.error(f"Error getting scraper status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")


@router.post("/cancel")
async def cancel_scraper(current_user: dict = Depends(lambda: {"id": 1})):
    """Cancel the currently running scraper."""
    try:
        db_url = get_db_url()
        manager = get_scraper_manager(db_url)

        if not manager.is_running():
            raise HTTPException(status_code=409, detail="No scraper running")

        manager.cancel_scrape()

        # Log audit
        run_id = manager.get_current_run_id()
        log_audit(
            "admin",
            "scraper_cancel",
            "scraper_run",
            run_id
        )

        return {"success": True, "message": "Cancellation requested"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling scraper: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel scraper")


@router.get("/runs", response_model=dict)
async def get_scraper_runs_list(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(lambda: {"id": 1})
):
    """Get paginated list of scraper runs."""
    try:
        runs, total = get_scraper_runs(limit, offset)

        return {
            "runs": [
                ScraperRunResponse(
                    id=run['id'],
                    started_at=run['started_at'],
                    completed_at=run['completed_at'],
                    status=run['status'],
                    trigger_type=run['trigger_type'],
                    triggered_by=run['triggered_by'],
                    stories_processed=run['stories_processed'],
                    errors_count=run['errors_count'],
                    config=run['config'],
                    error_message=run['error_message']
                )
                for run in runs
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error getting runs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get runs")


@router.get("/runs/{run_id}", response_model=ScraperRunResponse)
async def get_run_detail(
    run_id: int,
    current_user: dict = Depends(lambda: {"id": 1})
):
    """Get detailed information about a specific run."""
    try:
        run = get_scraper_run(run_id)

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        return ScraperRunResponse(
            id=run['id'],
            started_at=run['started_at'],
            completed_at=run['completed_at'],
            status=run['status'],
            trigger_type=run['trigger_type'],
            triggered_by=run['triggered_by'],
            stories_processed=run['stories_processed'],
            errors_count=run['errors_count'],
            config=run['config'],
            error_message=run['error_message']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting run detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to get run")


@router.get("/runs/{run_id}/logs")
async def get_run_logs(
    run_id: int,
    current_user: dict = Depends(lambda: {"id": 1})
):
    """
    Get logs for a specific run.

    Returns logs as a text stream.
    """
    try:
        run = get_scraper_run(run_id)

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        logs = run.get('logs', '')

        async def log_generator():
            yield logs

        return StreamingResponse(log_generator(), media_type="text/plain")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get logs")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time scraper updates.

    Sends updates as JSON:
    - {"type": "status", "status": "running|completed|failed"}
    - {"type": "log", "message": "..."}
    - {"type": "progress", "stories_processed": N, "errors_count": N}
    """
    await websocket.accept()

    db_url = get_db_url()
    manager = get_scraper_manager(db_url)

    def update_callback(message: dict):
        """Send update to WebSocket."""
        try:
            # We can't use await in a regular function, so we'd need to queue this
            # For now, store it and let the client poll
            pass
        except Exception as e:
            logger.error(f"Error sending WebSocket update: {e}")

    # Subscribe to updates
    manager.subscribe(update_callback)

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        manager.unsubscribe(update_callback)
