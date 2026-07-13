-- run this once in the supabase SQL editor for a new project.
-- three tables: jobs we've scored, decisions you've made on the ones we sent you,
-- and a one-row table just to remember our place in telegram's update feed.

create table jobs (
  id bigint generated always as identity primary key,
  source text not null,
  job_id text not null,
  title text not null,
  company text,
  location text,
  url text not null unique,
  score int,
  reason text,
  tailor_notes text,
  created_at timestamptz not null default now()
);

create table decisions (
  id bigint generated always as identity primary key,
  job_id bigint references jobs (id),
  telegram_message_id bigint not null,
  status text not null default 'pending', -- pending / interested / skipped
  created_at timestamptz not null default now()
);

create table bot_state (
  id int primary key,
  last_update_id bigint
);

insert into bot_state (id, last_update_id) values (1, null);

-- this project uses supabase's service_role key from github actions secrets,
-- so it's not relying on row level security for access control - the key
-- itself never leaves github's secret store. leaving RLS off for simplicity.
-- if you wanted to lock this down further (e.g. so a leaked key can only
-- insert, not read/delete), that's what RLS policies + the anon key are for.
