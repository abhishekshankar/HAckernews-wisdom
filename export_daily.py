import json
import os
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras


OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "daily-wisdom-data.json")


def get_env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def db_connect():
    db_url = get_env("SUPABASE_DB_URL")
    if os.environ.get("SUPABASE_FORCE_IPV4", "1") == "1":
        parsed = urlparse(db_url)
        if parsed.hostname:
            try:
                hostaddr = socket.gethostbyname(parsed.hostname)
                return psycopg2.connect(db_url, hostaddr=hostaddr)
            except socket.gaierror:
                pass
    return psycopg2.connect(db_url)


def fetch_latest_date(cur):
    cur.execute("select max(processed_at) from stories")
    row = cur.fetchone()
    return row[0]


def fetch_data(cur, target_date: datetime):
    cur.execute(
        """
        select s.id, s.title, s.url, s.score, s.author, s.processed_at, s.comment_count,
               a.url as article_url, a.content, a.reading_time
        from stories s
        left join articles a on a.story_id = s.id
        where date(s.processed_at) = %s
        """,
        (target_date.date(),)
    )
    stories = cur.fetchall()

    results = []
    for story in stories:
        story_id = story[0]
        cur.execute(
            """
            select c.name from categories c
            join story_categories sc on sc.category_id = c.id
            where sc.story_id = %s
            """,
            (story_id,)
        )
        categories = [row[0] for row in cur.fetchall()]

        cur.execute(
            """
            select cl.name from clusters cl
            join story_clusters sc on sc.cluster_id = cl.id
            where sc.story_id = %s
            """,
            (story_id,)
        )
        cluster_row = cur.fetchone()
        cluster = cluster_row[0] if cluster_row else "General"

        cur.execute(
            """
            select text, score from comments
            where story_id = %s and text is not null
            order by score desc nulls last
            limit 2
            """,
            (story_id,)
        )
        top_comments = [
            {"text": row[0], "score": row[1] or 0}
            for row in cur.fetchall()
        ]

        summary = (story[8] or "").strip()
        if len(summary) > 240:
            summary = summary[:240].rstrip() + "..."

        results.append({
            "id": story_id,
            "title": story[1],
            "hnUrl": story[2],
            "score": story[3] or 0,
            "commentCount": story[6] or 0,
            "author": story[4],
            "processedAt": story[5].date().isoformat(),
            "article": {
                "url": story[7],
                "summary": summary,
                "readingTime": story[9]
            },
            "topComments": top_comments,
            "categories": categories,
            "tags": [],
            "cluster": cluster
        })

    return results


def main():
    target = os.environ.get("EXPORT_DATE")
    conn = db_connect()
    with conn.cursor() as cur:
        if target:
            target_date = datetime.fromisoformat(target)
        else:
            latest = fetch_latest_date(cur)
            if not latest:
                raise RuntimeError("No stories found to export.")
            target_date = latest
        data = fetch_data(cur, target_date)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)

    conn.close()


if __name__ == "__main__":
    main()
