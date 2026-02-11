create table if not exists stories (
  id bigint primary key,
  title text,
  url text,
  score int,
  author text,
  created_at timestamp,
  processed_at timestamp,
  comment_count int,
  story_type text,
  source text default 'hn'
);

create table if not exists articles (
  id bigserial primary key,
  story_id bigint unique references stories(id) on delete cascade,
  url text,
  title text,
  author text,
  publish_date timestamp,
  reading_time text,
  content text,
  status text
);

create table if not exists comments (
  id bigint primary key,
  story_id bigint references stories(id) on delete cascade,
  parent_id bigint,
  author text,
  text text,
  score int,
  depth int,
  created_at timestamp
);

create table if not exists categories (
  id bigserial primary key,
  name text unique
);

create table if not exists story_categories (
  story_id bigint references stories(id) on delete cascade,
  category_id bigint references categories(id) on delete cascade,
  confidence_score float,
  is_manual boolean default false,
  primary key (story_id, category_id)
);

create table if not exists clusters (
  id bigserial primary key,
  name text unique,
  algorithm_version text,
  created_at timestamp
);

create table if not exists story_clusters (
  story_id bigint references stories(id) on delete cascade,
  cluster_id bigint references clusters(id) on delete cascade,
  similarity_score float,
  primary key (story_id, cluster_id)
);

-- Admin tables
create table if not exists admin_users (
  id bigserial primary key,
  username text unique not null,
  password_hash text not null,
  email text,
  created_at timestamp default now(),
  last_login timestamp
);

create table if not exists scraper_runs (
  id bigserial primary key,
  started_at timestamp not null,
  completed_at timestamp,
  status text not null,
  trigger_type text not null,
  triggered_by text,
  stories_processed int default 0,
  errors_count int default 0,
  config jsonb,
  logs text,
  error_message text
);

create table if not exists system_config (
  key text primary key,
  value jsonb not null,
  updated_at timestamp default now(),
  updated_by text
);

create table if not exists audit_log (
  id bigserial primary key,
  timestamp timestamp default now(),
  username text not null,
  action text not null,
  entity_type text,
  entity_id bigint,
  old_value jsonb,
  new_value jsonb
);

-- Indexes for admin tables
create index if not exists idx_scraper_runs_status on scraper_runs(status);
create index if not exists idx_scraper_runs_started on scraper_runs(started_at desc);
create index if not exists idx_audit_log_timestamp on audit_log(timestamp desc);
create index if not exists idx_audit_log_username on audit_log(username);

-- Default system configuration
insert into system_config (key, value, updated_by) values
  ('scraper.hn_limit', '100', 'system'),
  ('scraper.story_types', '["topstories","newstories","showstories","askstories","jobstories"]', 'system'),
  ('scraper.enabled', 'true', 'system'),
  ('categorization.keywords', '{"AI/ML":["ai","ml","llm","machine learning","neural","model"],"Security":["security","vuln","crypto","encryption","attack"],"Web Development":["web","frontend","backend","api","javascript"],"DevOps":["devops","sre","observability","k8s","kubernetes"],"Databases":["database","postgres","mysql","sqlite","query"],"Startups":["startup","founder","funding","venture"],"Career":["career","hiring","interview","salary"],"Show HN":["show hn"],"Ask HN":["ask hn"],"Jobs":["hiring","job","jobs"]}', 'system')
on conflict (key) do nothing;
