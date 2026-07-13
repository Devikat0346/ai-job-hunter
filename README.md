# ai-job-hunter

A little agent that goes and looks for jobs every morning, checks them against
my resume, and pings me on Telegram with the ones actually worth looking at.
I built this while job hunting for Forward Deployed Engineer roles - mostly
because I was tired of manually scrolling through job boards every day and
missing stuff.

Credit where it's due: this was inspired by [Abhijay Vuyyuru's "build your
own AI job hunting agent" post](https://abhijayvuyyuru.substack.com/p/build-your-own-ai-job-hunting-agent).
The original walks through building this with a Hostinger VPS, Apify's
LinkedIn scraper, and OpenAI/Anthropic - all of which cost money pretty
quickly. I rebuilt the same idea but swapped every piece for something free,
because I didn't want to hand out a credit card for a side project. Below is
what's different and why.

## What it actually does

1. Every morning, pull fresh job postings for keywords I care about
2. Skip anything already seen before (checked against a database)
3. Ask an LLM to score each new one against my resume, 1-10, with a reason
4. Send me the best ones on Telegram, with "interested" / "skip" buttons
5. When I tap a button, log that decision so there's a record of what I did

That's basically it. No auto-apply, no auto-generated cover letters getting
fired off without me looking - I still make every actual decision, the agent
just does the tedious filtering part.

## Why it's free instead of following the article exactly

| Piece | Article's approach | What I used instead | Why |
|---|---|---|---|
| Job data | Apify's LinkedIn scraper | [Remotive](https://remotive.com/api/remote-jobs) + [RemoteOK](https://remoteok.com/api) APIs | Both are free with no signup, and scraping LinkedIn directly is against their ToS. Coverage isn't 100% identical to LinkedIn but it's decent. |
| LLM | OpenAI / Anthropic (needs a card) | [Groq](https://console.groq.com) | Free API key, no card, and fast |
| Always-on server | Hostinger VPS (~$5/mo) | Two scheduled GitHub Actions workflows | GitHub Actions cron runs for free on a public repo - there's no server sitting around costing money 24/7 for something that only needs to run for a minute, twice an hour at most |
| Database | Supabase | Supabase (same) | Their free tier is genuinely free, no changes needed here |
| Messaging | Telegram | Telegram (same) | Also free, no reason to change it |

End result: this costs $0/month to run. The only "cost" is a few free
sign-ups (Telegram, Groq, Supabase).

## How it's put together

```
daily_scan.yml (cron, once a day)
  -> fetch_jobs.py     pulls postings from Remotive + RemoteOK
  -> db.py              checks which ones are new
  -> score_jobs.py      asks Groq to score the new ones against my resume
  -> db.py              saves every scored job (so we don't re-score it tomorrow)
  -> notify.py          telegrams me the top matches with Interested/Skip buttons

poll_replies.yml (cron, every 15 min)
  -> listen_replies.py  checks telegram for button taps since last time,
                         writes the decision (interested/skipped) back to supabase
```

I split the "find jobs" part and the "listen for my replies" part into two
separate scheduled jobs instead of one always-running process, since GitHub
Actions doesn't really do long-running background services - it just runs a
job to completion and stops. Polling every 15 minutes for replies is a
reasonable trade-off: it means there's no server bill, at the cost of my
button tap taking up to 15 minutes to register instead of being instant.

## Setup

### 1. Telegram bot
- Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, follow the prompts
- It'll give you a bot token - save that
- Message your new bot anything (so it can see your chat), then hit
  `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser and grab
  your numeric `chat.id` from the response

### 2. Groq
- Sign up at [console.groq.com](https://console.groq.com) (free, no card)
- Create an API key

### 3. Supabase
- New project at [supabase.com](https://supabase.com) (free tier)
- Open the SQL editor, paste in `supabase_schema.sql`, run it
- Grab your project URL and the `service_role` key from Project Settings > API

### 4. Wire it all up as GitHub secrets

```
gh secret set GROQ_API_KEY
gh secret set TELEGRAM_BOT_TOKEN
gh secret set TELEGRAM_CHAT_ID
gh secret set SUPABASE_URL
gh secret set SUPABASE_KEY
gh secret set RESUME_TEXT < resume/resume.txt
```

And a couple of non-secret repo variables for your search:

```
gh variable set SEARCH_KEYWORDS --body "forward deployed engineer,solutions engineer"
gh variable set SEARCH_LOCATION --body "remote"
```

### 5. Test it
Trigger it manually instead of waiting for the cron:

```
gh workflow run daily_scan.yml
gh workflow run poll_replies.yml
```

Then check the Actions tab for logs, and your Telegram for messages.

## Running locally

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill it in
export $(cat .env | xargs)
python -m job_hunter.main
```

## A few honest limitations

- Job coverage isn't as broad as scraping LinkedIn directly would be -
  Remotive and RemoteOK skew towards remote/tech roles. Good enough for what
  I needed, not a total replacement for browsing LinkedIn yourself.
- The scoring is only as good as what's in the job description text - some
  postings are thin on detail and get scored lower than they maybe deserve.
- No resume rewriting/auto-tailoring - it gives tailoring *suggestions*, not
  a rewritten resume. I didn't want it inventing experience I don't have,
  which is a real risk with full auto-rewrite approaches.
- The 15-minute reply polling means button taps aren't instant. Fine for me,
  might not be for everyone.

## About this project

This is one of a handful of projects I built to demonstrate the kind of
end-to-end ownership a Forward Deployed Engineer role needs - scoping a
problem, picking pragmatic (and cheap) tools, and shipping something that
actually works day to day, not just a demo.
