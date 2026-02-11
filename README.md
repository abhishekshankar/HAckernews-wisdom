# Hackernews Wisdom Dashboard

Open `daily-wisdom.html` in a browser to view the dashboard.

## Data Scraping (Supabase + GitHub Actions)

## Live Supabase (Optional)
If you want the dashboard to read directly from Supabase:
1. Create a `daily_wisdom_view` in Supabase (see below).
2. Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `daily-wisdom.js`.

### Suggested view (run in Supabase SQL editor)
```sql
create or replace view daily_wisdom_view as
select
  s.id,
  s.title,
  s.url as "hnUrl",
  s.score,
  s.comment_count as "commentCount",
  s.author,
  s.processed_at::date as "processedAt",
  jsonb_build_object(
    'url', a.url,
    'summary', left(coalesce(a.content, ''), 240),
    'readingTime', a.reading_time
  ) as article,
  (
    select jsonb_agg(jsonb_build_object('text', c.text, 'score', c.score))
    from (
      select text, score
      from comments
      where story_id = s.id and text is not null
      order by score desc nulls last
      limit 2
    ) c
  ) as "topComments",
  (
    select array_agg(cat.name)
    from story_categories sc
    join categories cat on cat.id = sc.category_id
    where sc.story_id = s.id
  ) as categories,
  '[]'::jsonb as tags,
  (
    select cl.name
    from story_clusters sc2
    join clusters cl on cl.id = sc2.cluster_id
    where sc2.story_id = s.id
    limit 1
  ) as cluster
from stories s
left join articles a on a.story_id = s.id;
```

### Required secret
Set `SUPABASE_DB_URL` in GitHub repo secrets.

### Manual run
```bash
SUPABASE_DB_URL="..." python HAckernews-wisdom/scrape_hn.py
SUPABASE_DB_URL="..." python HAckernews-wisdom/export_daily.py
```

### Daily schedule
The GitHub Action `.github/workflows/daily-scrape.yml` runs once per day at 03:00 UTC.
