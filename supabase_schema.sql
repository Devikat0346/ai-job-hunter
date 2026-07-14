-- run this once in the supabase SQL editor for a new project.
-- two tables: jobs we've scored, and decisions you've made on the ones we sent you.
-- (used to have a third table to track our place in a polling feed, back when
-- this used telegram - whatsapp pushes replies straight to a webhook instead,
-- so there's nothing to keep track of between runs anymore)

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
  whatsapp_message_id text not null,
  status text not null default 'pending', -- pending / interested / skipped
  created_at timestamptz not null default now()
);

-- this project uses supabase's service_role key from github actions secrets,
-- so it's not relying on row level security for access control - the key
-- itself never leaves github's secret store. leaving RLS off for simplicity.
-- if you wanted to lock this down further (e.g. so a leaked key can only
-- insert, not read/delete), that's what RLS policies + the anon key are for.
