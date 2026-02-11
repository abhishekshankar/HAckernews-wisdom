"""Pydantic models for request/response validation."""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


# Authentication models
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]


# Scraper models
class ScraperTriggerRequest(BaseModel):
    limit: Optional[int] = 100
    story_types: Optional[List[str]] = None


class ScraperRunResponse(BaseModel):
    id: int
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    trigger_type: str
    triggered_by: Optional[str]
    stories_processed: int
    errors_count: int
    config: Optional[Dict[str, Any]]
    error_message: Optional[str]


class ScraperStatusResponse(BaseModel):
    is_running: bool
    current_run: Optional[ScraperRunResponse]
    last_completed: Optional[ScraperRunResponse]


# Data models
class StoryResponse(BaseModel):
    id: int
    title: str
    url: Optional[str]
    score: int
    author: Optional[str]
    created_at: datetime
    processed_at: datetime
    comment_count: int
    story_type: Optional[str]


class StoryUpdateRequest(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    score: Optional[int] = None
    author: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    story_count: Optional[int] = 0


class CategoryCreateRequest(BaseModel):
    name: str


class CategoryUpdateRequest(BaseModel):
    name: str


class ClusterResponse(BaseModel):
    id: int
    name: str
    story_count: Optional[int] = 0
    algorithm_version: Optional[str]


class ClusterCreateRequest(BaseModel):
    name: str
    algorithm_version: Optional[str] = "heuristic-v1"


class ClusterUpdateRequest(BaseModel):
    name: str


class StoryCategoryAssignRequest(BaseModel):
    category_ids: List[int]
    is_manual: bool = True


# Analytics models
class AnalyticsOverviewResponse(BaseModel):
    total_stories: int
    total_comments: int
    stories_last_7_days: int
    stories_last_30_days: int
    avg_score: float
    avg_comment_count: float
    scraper_success_rate: float
    top_categories: List[Dict[str, Any]]
    top_authors: List[Dict[str, Any]]


class AnalyticsScraperStatsResponse(BaseModel):
    total_runs: int
    success_count: int
    failed_count: int
    success_rate: float
    avg_duration_seconds: float
    avg_stories_per_run: float
    recent_runs: List[ScraperRunResponse]


# Configuration models
class ConfigResponse(BaseModel):
    scraper: Dict[str, Any]
    categorization: Dict[str, Any]


class ConfigUpdateRequest(BaseModel):
    scraper: Optional[Dict[str, Any]] = None
    categorization: Optional[Dict[str, Any]] = None


class KeywordsUpdateRequest(BaseModel):
    category: str
    keywords: List[str]


class CategorizationTestRequest(BaseModel):
    text: str


class CategorizationTestResponse(BaseModel):
    categories: List[str]
    confidence_scores: Dict[str, float]


# Public config (for frontend)
class PublicConfigResponse(BaseModel):
    supabase_url: str
    supabase_anon_key: str
