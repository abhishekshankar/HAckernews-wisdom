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
  story_id bigint references stories(id) on delete cascade,
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
  name text,
  algorithm_version text,
  created_at timestamp
);

create table if not exists story_clusters (
  story_id bigint references stories(id) on delete cascade,
  cluster_id bigint references clusters(id) on delete cascade,
  similarity_score float,
  primary key (story_id, cluster_id)
);
