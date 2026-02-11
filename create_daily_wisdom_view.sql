-- Create daily_wisdom_view for dashboard integration
-- This view formats data for the frontend dashboard

create or replace view daily_wisdom_view as
select
  s.id,
  s.title,
  s.url as hnUrl,
  s.score,
  s.comment_count as commentCount,
  s.author,
  s.processed_at as processedAt,
  coalesce(a.url, '') as article_url,
  coalesce(a.content, '') as article_summary,
  coalesce(a.reading_time, '') as reading_time,
  -- Aggregate categories as array
  (
    select array_agg(c.name)
    from story_categories sc
    join categories c on c.id = sc.category_id
    where sc.story_id = s.id
  ) as categories,
  -- Get primary cluster
  (
    select cl.name
    from story_clusters scl
    join clusters cl on cl.id = scl.cluster_id
    where scl.story_id = s.id
    limit 1
  ) as cluster,
  -- Aggregate top 2 comments
  (
    select array_agg(json_build_object('text', text, 'score', score) order by score desc nulls last)
    from comments
    where story_id = s.id
      and text is not null
    limit 2
  ) as topComments
from stories s
left join lateral (
  select url, content, reading_time
  from articles
  where articles.story_id = s.id
  limit 1
) a on true
where s.processed_at is not null
order by s.processed_at desc, s.id desc;

-- Enable RLS if needed (optional)
alter table stories enable row level security;
alter table articles enable row level security;
alter table comments enable row level security;
alter table categories enable row level security;
alter table clusters enable row level security;

-- Grant select access to anon role for the view
grant select on daily_wisdom_view to anon;

-- If you have RLS policies, add one for anon role:
-- create policy "Allow anon select" on stories
--   for select using (true);
