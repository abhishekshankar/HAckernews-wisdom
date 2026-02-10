import json
import os
import socket
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras
import requests
from bs4 import BeautifulSoup
from readability import Document

HN_BASE = "https://hacker-news.firebaseio.com/v0"
HN_TYPES = ["topstories", "newstories", "showstories", "askstories", "jobstories"]
DEFAULT_LIMIT = 100
USER_AGENT = "DailyWisdomBot/1.0 (+https://example.com)"
HN_RETRIES = 4

CATEGORY_KEYWORDS = {
    "AI/ML": ["ai", "ml", "llm", "machine learning", "neural", "model"],
    "Security": ["security", "vuln", "crypto", "encryption", "attack"],
    "Web Development": ["web", "frontend", "backend", "api", "javascript"],
    "DevOps": ["devops", "sre", "observability", "k8s", "kubernetes"],
    "Databases": ["database", "postgres", "mysql", "sqlite", "query"],
    "Startups": ["startup", "founder", "funding", "venture"],
    "Career": ["career", "hiring", "interview", "salary"],
    "Show HN": ["show hn"],
    "Ask HN": ["ask hn"],
    "Jobs": ["hiring", "job", "jobs"]
}


def get_env(name: str, default: Optional[str] = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def db_connect():
    db_url = get_env("SUPABASE_DB_URL")
    parsed = urlparse(db_url)
    if os.environ.get("SUPABASE_FORCE_IPV4", "1") == "1" and parsed.hostname:
        try:
            hostaddr = socket.gethostbyname(parsed.hostname)
        except socket.gaierror:
            hostaddr = None
    else:
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
    )


def ensure_schema(conn):
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as handle:
        schema_sql = handle.read()
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    conn.commit()


def hn_get(path: str):
    url = f"{HN_BASE}/{path}.json"
    for attempt in range(1, HN_RETRIES + 1):
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            if attempt == HN_RETRIES:
                print(f"Failed to fetch {url}: {exc}")
                return None
            time.sleep(1.5 * attempt)


def fetch_story_ids(limit: int) -> Dict[str, List[int]]:
    results = {}
    for story_type in HN_TYPES:
        ids = hn_get(story_type) or []
        results[story_type] = ids[:limit]
        time.sleep(0.2)
    return results


def fetch_item(item_id: int) -> Optional[dict]:
    data = hn_get(f"item/{item_id}")
    time.sleep(0.2)
    return data


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return " ".join(soup.stripped_strings)


def fetch_article(url: str) -> dict:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
        doc = Document(resp.text)
        title = doc.short_title()
        content_html = doc.summary()
        content_text = html_to_text(content_html)
        words = len(content_text.split())
        reading_time = f"{max(1, words // 200)} min"
        return {
            "url": url,
            "title": title,
            "author": None,
            "publish_date": None,
            "reading_time": reading_time,
            "content": content_text,
            "status": "ok"
        }
    except Exception:
        return {
            "url": url,
            "title": None,
            "author": None,
            "publish_date": None,
            "reading_time": None,
            "content": None,
            "status": "failed"
        }


def categorize(text: str) -> List[str]:
    lowered = text.lower()
    matches = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            matches.append(category)
    return matches or ["General"]


def upsert_story(cur, story: dict, story_type: str, processed_at: datetime):
    cur.execute(
        """
        insert into stories (id, title, url, score, author, created_at, processed_at, comment_count, story_type)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (id) do update set
          title = excluded.title,
          url = excluded.url,
          score = excluded.score,
          author = excluded.author,
          created_at = excluded.created_at,
          processed_at = excluded.processed_at,
          comment_count = excluded.comment_count,
          story_type = excluded.story_type
        """,
        (
            story["id"],
            story.get("title"),
            story.get("url"),
            story.get("score"),
            story.get("by"),
            datetime.fromtimestamp(story.get("time", 0), tz=timezone.utc),
            processed_at,
            story.get("descendants", 0),
            story_type
        )
    )


def upsert_article(cur, story_id: int, article: dict):
    cur.execute(
        """
        insert into articles (story_id, url, title, author, publish_date, reading_time, content, status)
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict do nothing
        """,
        (
            story_id,
            article.get("url"),
            article.get("title"),
            article.get("author"),
            article.get("publish_date"),
            article.get("reading_time"),
            article.get("content"),
            article.get("status")
        )
    )


def upsert_comment(cur, comment: dict, story_id: int, depth: int):
    cur.execute(
        """
        insert into comments (id, story_id, parent_id, author, text, score, depth, created_at)
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (id) do update set
          text = excluded.text,
          score = excluded.score,
          depth = excluded.depth
        """,
        (
            comment["id"],
            story_id,
            comment.get("parent"),
            comment.get("by"),
            comment.get("text"),
            comment.get("score"),
            depth,
            datetime.fromtimestamp(comment.get("time", 0), tz=timezone.utc)
        )
    )


def store_categories(cur, story_id: int, categories: List[str]):
    for category in categories:
        cur.execute("insert into categories (name) values (%s) on conflict (name) do nothing", (category,))
        cur.execute("select id from categories where name = %s", (category,))
        category_id = cur.fetchone()[0]
        cur.execute(
            """
            insert into story_categories (story_id, category_id, confidence_score, is_manual)
            values (%s, %s, %s, %s)
            on conflict (story_id, category_id) do nothing
            """,
            (story_id, category_id, 0.7, False)
        )


def store_cluster(cur, story_id: int, cluster_name: str):
    cur.execute(
        """
        insert into clusters (name, algorithm_version, created_at)
        values (%s, %s, %s)
        on conflict do nothing
        """,
        (cluster_name, "heuristic-v1", datetime.now(tz=timezone.utc))
    )
    cur.execute("select id from clusters where name = %s", (cluster_name,))
    cluster_id = cur.fetchone()[0]
    cur.execute(
        """
        insert into story_clusters (story_id, cluster_id, similarity_score)
        values (%s, %s, %s)
        on conflict (story_id, cluster_id) do nothing
        """,
        (story_id, cluster_id, 0.6)
    )


def fetch_comments(story_id: int, kids: List[int]) -> List[dict]:
    comments = []
    stack = [(kid, 0) for kid in kids]
    while stack:
        comment_id, depth = stack.pop()
        item = fetch_item(comment_id)
        if not item or item.get("type") != "comment":
            continue
        comments.append({"item": item, "depth": depth})
        child_ids = item.get("kids", [])
        for child_id in child_ids:
            stack.append((child_id, depth + 1))
    return comments


def main():
    limit = int(os.environ.get("HN_LIMIT", DEFAULT_LIMIT))
    conn = db_connect()
    ensure_schema(conn)
    processed_at = datetime.now(tz=timezone.utc)

    ids_by_type = fetch_story_ids(limit)

    with conn.cursor() as cur:
        for story_type, ids in ids_by_type.items():
            for story_id in ids:
                story = fetch_item(story_id)
                if not story or story.get("type") != "story":
                    continue
                upsert_story(cur, story, story_type, processed_at)

                if story.get("url"):
                    article = fetch_article(story["url"])
                    upsert_article(cur, story["id"], article)
                    text_for_category = f"{story.get('title', '')} {article.get('content', '')}"
                else:
                    text_for_category = story.get("title", "")

                categories = categorize(text_for_category)
                store_categories(cur, story["id"], categories)
                store_cluster(cur, story["id"], categories[0])

                kids = story.get("kids", [])
                for comment in fetch_comments(story["id"], kids):
                    upsert_comment(cur, comment["item"], story["id"], comment["depth"])

                conn.commit()

    conn.close()


if __name__ == "__main__":
    main()
