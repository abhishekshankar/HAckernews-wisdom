"""Data management API endpoints for stories, categories, and clusters."""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from ..database import (
    get_db_url,
    execute_query,
    execute_insert,
    execute_update,
    execute_delete,
    log_audit
)
from ..models import (
    StoryResponse,
    CategoryResponse,
    CategoryCreateRequest,
    CategoryUpdateRequest,
    ClusterResponse,
    ClusterCreateRequest,
    ClusterUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["data"])


# ===== STORIES ENDPOINTS =====

@router.get("/stories", response_model=dict)
async def list_stories(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    category: Optional[int] = Query(None),
    cluster: Optional[int] = Query(None),
    min_score: int = Query(0, ge=0),
    story_type: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|score|comment_count)$"),
    order: str = Query("desc", pattern="^(asc|desc)$")
):
    """Get paginated list of stories with filtering and search."""
    try:
        # Build query
        where_clauses = ["s.score >= %s"]
        params = [min_score]

        if search:
            where_clauses.append("(s.title ILIKE %s OR a.extracted_text ILIKE %s)")
            search_term = f"%{search}%"
            params.extend([search_term, search_term])

        if story_type:
            where_clauses.append("s.story_type = %s")
            params.append(story_type)

        # Build category filter
        category_join = ""
        if category:
            category_join = """
                INNER JOIN story_categories sc ON s.id = sc.story_id
            """
            where_clauses.append("sc.category_id = %s")
            params.append(category)

        # Build cluster filter
        cluster_join = ""
        if cluster:
            cluster_join = """
                INNER JOIN story_clusters scl ON s.id = scl.story_id
            """
            where_clauses.append("scl.cluster_id = %s")
            params.append(cluster)

        where_clause = " AND ".join(where_clauses)

        # Get total count
        count_query = f"""
            SELECT COUNT(DISTINCT s.id) as count
            FROM stories s
            LEFT JOIN articles a ON s.id = a.story_id
            LEFT JOIN story_categories sc ON s.id = sc.story_id
            LEFT JOIN story_clusters scl ON s.id = scl.story_id
            {category_join}
            {cluster_join}
            WHERE {where_clause}
        """
        total_result = execute_query(count_query, tuple(params), fetch=True, fetch_all=False)
        total = total_result['count'] if total_result else 0

        # Get paginated results
        query = f"""
            SELECT DISTINCT
                s.id, s.title, s.url, s.score, s.author,
                s.created_at, s.comment_count, s.story_type,
                ARRAY_AGG(DISTINCT c.id) FILTER (WHERE c.id IS NOT NULL) as category_ids,
                ARRAY_AGG(DISTINCT c.name) FILTER (WHERE c.id IS NOT NULL) as category_names,
                ARRAY_AGG(DISTINCT scl.cluster_id) FILTER (WHERE scl.cluster_id IS NOT NULL) as cluster_ids
            FROM stories s
            LEFT JOIN articles a ON s.id = a.story_id
            LEFT JOIN story_categories sc ON s.id = sc.story_id
            LEFT JOIN categories c ON sc.category_id = c.id
            LEFT JOIN story_clusters scl ON s.id = scl.story_id
            {category_join}
            {cluster_join}
            WHERE {where_clause}
            GROUP BY s.id, s.title, s.url, s.score, s.author, s.created_at, s.comment_count, s.story_type
            ORDER BY s.{sort_by} {order.upper()}
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        results = execute_query(query, tuple(params), fetch=True, fetch_all=True)

        stories = []
        for row in results or []:
            stories.append({
                "id": row['id'],
                "title": row['title'],
                "url": row['url'],
                "score": row['score'],
                "author": row['author'],
                "created_at": row['created_at'],
                "comment_count": row['comment_count'],
                "story_type": row['story_type'],
                "category_ids": row['category_ids'] or [],
                "category_names": row['category_names'] or [],
                "cluster_ids": row['cluster_ids'] or []
            })

        return {
            "stories": stories,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error listing stories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stories: {str(e)}")


@router.get("/stories/{story_id}", response_model=dict)
async def get_story_detail(story_id: int):
    """Get detailed information about a specific story."""
    try:
        query = """
            SELECT s.id, s.title, s.url, s.score, s.author,
                   s.created_at, s.processed_at, s.comment_count, s.story_type,
                   a.extracted_text, a.summary,
                   ARRAY_AGG(DISTINCT c.id) FILTER (WHERE c.id IS NOT NULL) as category_ids,
                   ARRAY_AGG(DISTINCT c.name) FILTER (WHERE c.id IS NOT NULL) as category_names,
                   ARRAY_AGG(DISTINCT scl.cluster_id) FILTER (WHERE scl.cluster_id IS NOT NULL) as cluster_ids
            FROM stories s
            LEFT JOIN articles a ON s.id = a.story_id
            LEFT JOIN story_categories sc ON s.id = sc.story_id
            LEFT JOIN categories c ON sc.category_id = c.id
            LEFT JOIN story_clusters scl ON s.id = scl.story_id
            WHERE s.id = %s
            GROUP BY s.id, a.id
        """

        result = execute_query(query, (story_id,), fetch=True, fetch_all=False)

        if not result:
            raise HTTPException(status_code=404, detail="Story not found")

        return {
            "id": result['id'],
            "title": result['title'],
            "url": result['url'],
            "score": result['score'],
            "author": result['author'],
            "created_at": result['created_at'],
            "processed_at": result['processed_at'],
            "comment_count": result['comment_count'],
            "story_type": result['story_type'],
            "extracted_text": result['extracted_text'],
            "summary": result['summary'],
            "category_ids": result['category_ids'] or [],
            "category_names": result['category_names'] or [],
            "cluster_ids": result['cluster_ids'] or []
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get story")


@router.put("/stories/{story_id}")
async def update_story(story_id: int, updates: dict):
    """Update story fields (title, url, etc)."""
    try:
        # Validate story exists
        exists = execute_query(
            "SELECT 1 FROM stories WHERE id = %s",
            (story_id,),
            fetch=True,
            fetch_all=False
        )

        if not exists:
            raise HTTPException(status_code=404, detail="Story not found")

        # Build update query dynamically
        allowed_fields = {"title", "url", "score", "author", "comment_count"}
        update_parts = []
        params = []

        for field, value in updates.items():
            if field in allowed_fields:
                update_parts.append(f"{field} = %s")
                params.append(value)

        if not update_parts:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        params.append(story_id)

        query = f"UPDATE stories SET {', '.join(update_parts)} WHERE id = %s"
        execute_update(query, tuple(params))

        # Log audit
        log_audit(
            "admin",
            "story_update",
            "story",
            story_id,
            new_value=updates
        )

        return {"success": True, "story_id": story_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update story")


@router.delete("/stories/{story_id}")
async def delete_story(story_id: int):
    """Delete a story and cascade delete related data."""
    try:
        # Check if story exists
        exists = execute_query(
            "SELECT 1 FROM stories WHERE id = %s",
            (story_id,),
            fetch=True,
            fetch_all=False
        )

        if not exists:
            raise HTTPException(status_code=404, detail="Story not found")

        # Delete story (cascades to articles, story_categories, story_clusters)
        execute_delete(
            "DELETE FROM stories WHERE id = %s",
            (story_id,)
        )

        # Log audit
        log_audit(
            "admin",
            "story_delete",
            "story",
            story_id
        )

        return {"success": True, "story_id": story_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting story: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete story")


@router.put("/stories/{story_id}/categories")
async def assign_story_categories(story_id: int, category_ids: List[int]):
    """Assign categories to a story (replaces existing)."""
    try:
        # Verify story exists
        exists = execute_query(
            "SELECT 1 FROM stories WHERE id = %s",
            (story_id,),
            fetch=True,
            fetch_all=False
        )

        if not exists:
            raise HTTPException(status_code=404, detail="Story not found")

        # Remove existing category assignments
        execute_delete(
            "DELETE FROM story_categories WHERE story_id = %s",
            (story_id,)
        )

        # Add new category assignments
        for cat_id in category_ids:
            # Verify category exists
            cat_exists = execute_query(
                "SELECT 1 FROM categories WHERE id = %s",
                (cat_id,),
                fetch=True,
                fetch_all=False
            )

            if not cat_exists:
                raise HTTPException(status_code=400, detail=f"Category {cat_id} not found")

            execute_insert(
                """INSERT INTO story_categories (story_id, category_id, is_manual)
                   VALUES (%s, %s, true)""",
                (story_id, cat_id)
            )

        # Log audit
        log_audit(
            "admin",
            "story_categories_update",
            "story",
            story_id,
            new_value={"category_ids": category_ids}
        )

        return {"success": True, "story_id": story_id, "category_ids": category_ids}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to assign categories")


# ===== CATEGORIES ENDPOINTS =====

@router.get("/categories", response_model=dict)
async def list_categories(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get list of all categories with story counts."""
    try:
        # Get total count
        count_result = execute_query(
            "SELECT COUNT(*) as count FROM categories",
            fetch=True,
            fetch_all=False
        )
        total = count_result['count'] if count_result else 0

        # Get categories with counts
        query = """
            SELECT c.id, c.name, COUNT(DISTINCT sc.story_id) as story_count
            FROM categories c
            LEFT JOIN story_categories sc ON c.id = sc.category_id
            GROUP BY c.id, c.name
            ORDER BY c.name ASC
            LIMIT %s OFFSET %s
        """

        results = execute_query(query, (limit, offset), fetch=True, fetch_all=True)

        categories = []
        for row in results or []:
            categories.append({
                "id": row['id'],
                "name": row['name'],
                "story_count": row['story_count'] or 0
            })

        return {
            "categories": categories,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error listing categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get categories")


@router.post("/categories", response_model=dict)
async def create_category(request: CategoryCreateRequest):
    """Create a new category."""
    try:
        # Check if category already exists
        exists = execute_query(
            "SELECT id FROM categories WHERE name = %s",
            (request.name,),
            fetch=True,
            fetch_all=False
        )

        if exists:
            raise HTTPException(status_code=409, detail="Category already exists")

        # Create category
        cat_id = execute_insert(
            "INSERT INTO categories (name) VALUES (%s) RETURNING id",
            (request.name,)
        )

        # Log audit
        log_audit(
            "admin",
            "category_create",
            "category",
            cat_id,
            new_value={"name": request.name}
        )

        return {
            "success": True,
            "id": cat_id,
            "name": request.name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create category")


@router.put("/categories/{category_id}")
async def update_category(category_id: int, request: CategoryUpdateRequest):
    """Update a category."""
    try:
        # Check if category exists
        exists = execute_query(
            "SELECT name FROM categories WHERE id = %s",
            (category_id,),
            fetch=True,
            fetch_all=False
        )

        if not exists:
            raise HTTPException(status_code=404, detail="Category not found")

        old_name = exists['name']

        # Check if new name already exists
        if request.name != old_name:
            name_exists = execute_query(
                "SELECT 1 FROM categories WHERE name = %s AND id != %s",
                (request.name, category_id),
                fetch=True,
                fetch_all=False
            )

            if name_exists:
                raise HTTPException(status_code=409, detail="Category name already exists")

        # Update category
        execute_update(
            "UPDATE categories SET name = %s WHERE id = %s",
            (request.name, category_id)
        )

        # Log audit
        log_audit(
            "admin",
            "category_update",
            "category",
            category_id,
            old_value={"name": old_name},
            new_value={"name": request.name}
        )

        return {"success": True, "id": category_id, "name": request.name}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update category")


@router.delete("/categories/{category_id}")
async def delete_category(category_id: int, reassign_to: Optional[int] = Query(None)):
    """Delete a category (optionally reassign stories to another category)."""
    try:
        # Check if category exists
        exists = execute_query(
            "SELECT name FROM categories WHERE id = %s",
            (category_id,),
            fetch=True,
            fetch_all=False
        )

        if not exists:
            raise HTTPException(status_code=404, detail="Category not found")

        category_name = exists['name']

        # If reassigning, verify target category exists
        if reassign_to:
            target_exists = execute_query(
                "SELECT 1 FROM categories WHERE id = %s",
                (reassign_to,),
                fetch=True,
                fetch_all=False
            )

            if not target_exists:
                raise HTTPException(status_code=400, detail="Target category not found")

            # Reassign stories
            execute_update(
                "UPDATE story_categories SET category_id = %s WHERE category_id = %s",
                (reassign_to, category_id)
            )

        # Delete category
        execute_delete(
            "DELETE FROM categories WHERE id = %s",
            (category_id,)
        )

        # Log audit
        log_audit(
            "admin",
            "category_delete",
            "category",
            category_id,
            old_value={"name": category_name, "reassigned_to": reassign_to}
        )

        return {"success": True, "id": category_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete category")


# ===== CLUSTERS ENDPOINTS =====

@router.get("/clusters", response_model=dict)
async def list_clusters(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get list of all clusters with story counts."""
    try:
        # Get total count
        count_result = execute_query(
            "SELECT COUNT(*) as count FROM clusters",
            fetch=True,
            fetch_all=False
        )
        total = count_result['count'] if count_result else 0

        # Get clusters with counts
        query = """
            SELECT c.id, c.name, COUNT(DISTINCT scl.story_id) as story_count, c.created_at
            FROM clusters c
            LEFT JOIN story_clusters scl ON c.id = scl.cluster_id
            GROUP BY c.id, c.name, c.created_at
            ORDER BY c.created_at DESC
            LIMIT %s OFFSET %s
        """

        results = execute_query(query, (limit, offset), fetch=True, fetch_all=True)

        clusters = []
        for row in results or []:
            clusters.append({
                "id": row['id'],
                "name": row['name'],
                "story_count": row['story_count'] or 0,
                "created_at": row['created_at']
            })

        return {
            "clusters": clusters,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error listing clusters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get clusters")


@router.post("/clusters", response_model=dict)
async def create_cluster(request: ClusterCreateRequest):
    """Create a new cluster."""
    try:
        # Check if cluster already exists
        exists = execute_query(
            "SELECT id FROM clusters WHERE name = %s",
            (request.name,),
            fetch=True,
            fetch_all=False
        )

        if exists:
            raise HTTPException(status_code=409, detail="Cluster already exists")

        # Create cluster
        cluster_id = execute_insert(
            """INSERT INTO clusters (name, algorithm_version, created_at)
               VALUES (%s, %s, NOW()) RETURNING id""",
            (request.name, "manual")
        )

        # Log audit
        log_audit(
            "admin",
            "cluster_create",
            "cluster",
            cluster_id,
            new_value={"name": request.name}
        )

        return {
            "success": True,
            "id": cluster_id,
            "name": request.name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating cluster: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create cluster")


@router.put("/clusters/{cluster_id}")
async def update_cluster(cluster_id: int, request: ClusterUpdateRequest):
    """Update a cluster."""
    try:
        # Check if cluster exists
        exists = execute_query(
            "SELECT name FROM clusters WHERE id = %s",
            (cluster_id,),
            fetch=True,
            fetch_all=False
        )

        if not exists:
            raise HTTPException(status_code=404, detail="Cluster not found")

        old_name = exists['name']

        # Check if new name already exists
        if request.name != old_name:
            name_exists = execute_query(
                "SELECT 1 FROM clusters WHERE name = %s AND id != %s",
                (request.name, cluster_id),
                fetch=True,
                fetch_all=False
            )

            if name_exists:
                raise HTTPException(status_code=409, detail="Cluster name already exists")

        # Update cluster
        execute_update(
            "UPDATE clusters SET name = %s WHERE id = %s",
            (request.name, cluster_id)
        )

        # Log audit
        log_audit(
            "admin",
            "cluster_update",
            "cluster",
            cluster_id,
            old_value={"name": old_name},
            new_value={"name": request.name}
        )

        return {"success": True, "id": cluster_id, "name": request.name}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cluster: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update cluster")


@router.delete("/clusters/{cluster_id}")
async def delete_cluster(cluster_id: int, reassign_to: Optional[int] = Query(None)):
    """Delete a cluster (optionally reassign stories to another cluster)."""
    try:
        # Check if cluster exists
        exists = execute_query(
            "SELECT name FROM clusters WHERE id = %s",
            (cluster_id,),
            fetch=True,
            fetch_all=False
        )

        if not exists:
            raise HTTPException(status_code=404, detail="Cluster not found")

        cluster_name = exists['name']

        # If reassigning, verify target cluster exists
        if reassign_to:
            target_exists = execute_query(
                "SELECT 1 FROM clusters WHERE id = %s",
                (reassign_to,),
                fetch=True,
                fetch_all=False
            )

            if not target_exists:
                raise HTTPException(status_code=400, detail="Target cluster not found")

            # Reassign stories
            execute_update(
                "UPDATE story_clusters SET cluster_id = %s WHERE cluster_id = %s",
                (reassign_to, cluster_id)
            )

        # Delete cluster
        execute_delete(
            "DELETE FROM clusters WHERE id = %s",
            (cluster_id,)
        )

        # Log audit
        log_audit(
            "admin",
            "cluster_delete",
            "cluster",
            cluster_id,
            old_value={"name": cluster_name, "reassigned_to": reassign_to}
        )

        return {"success": True, "id": cluster_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting cluster: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete cluster")


# ===== BULK OPERATIONS =====

@router.post("/bulk/recategorize")
async def bulk_recategorize(
    story_ids: List[int],
    category_ids: List[int],
    replace: bool = Query(True)
):
    """Apply categories to multiple stories."""
    try:
        if not story_ids or not category_ids:
            raise HTTPException(status_code=400, detail="story_ids and category_ids required")

        # Verify all categories exist
        placeholders = ",".join(["%s"] * len(category_ids))
        cat_check = execute_query(
            f"SELECT COUNT(*) as count FROM categories WHERE id IN ({placeholders})",
            tuple(category_ids),
            fetch=True,
            fetch_all=False
        )

        if cat_check['count'] != len(category_ids):
            raise HTTPException(status_code=400, detail="One or more categories not found")

        updated_count = 0

        for story_id in story_ids:
            # Verify story exists
            exists = execute_query(
                "SELECT 1 FROM stories WHERE id = %s",
                (story_id,),
                fetch=True,
                fetch_all=False
            )

            if not exists:
                continue

            if replace:
                # Remove existing categories
                execute_delete(
                    "DELETE FROM story_categories WHERE story_id = %s",
                    (story_id,)
                )

            # Add new categories
            for cat_id in category_ids:
                try:
                    execute_insert(
                        """INSERT INTO story_categories (story_id, category_id, is_manual)
                           VALUES (%s, %s, true)
                           ON CONFLICT (story_id, category_id) DO NOTHING""",
                        (story_id, cat_id)
                    )
                    updated_count += 1
                except Exception:
                    pass

        # Log audit
        log_audit(
            "admin",
            "bulk_recategorize",
            "story",
            None,
            new_value={"story_count": len(story_ids), "category_ids": category_ids}
        )

        return {
            "success": True,
            "stories_updated": len(story_ids),
            "total_assignments": updated_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk recategorize: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to recategorize stories")


@router.post("/bulk/delete")
async def bulk_delete(story_ids: List[int]):
    """Delete multiple stories."""
    try:
        if not story_ids:
            raise HTTPException(status_code=400, detail="story_ids required")

        deleted_count = 0

        for story_id in story_ids:
            try:
                execute_delete(
                    "DELETE FROM stories WHERE id = %s",
                    (story_id,)
                )
                deleted_count += 1
            except Exception:
                pass

        # Log audit
        log_audit(
            "admin",
            "bulk_delete",
            "story",
            None,
            new_value={"story_count": deleted_count}
        )

        return {
            "success": True,
            "deleted_count": deleted_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete stories")
