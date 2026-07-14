# ai-job-hunter

A little agent that goes and looks for jobs every morning, checks them against
my resume, and pings me on WhatsApp with the ones actually worth looking at.
I built this while job hunting for Forward Deployed Engineer roles - mostly
because I was tired of manually scrolling through job boards every day and
missing stuff.

Credit where it's due: this was inspired by [Abhijay Vuyyuru's "build your
own AI job hunting agent" post](https://abhijayvuyyuru.substack.com/p/build-your-own-ai-job-hunting-agent).
The original walks through building this with a Hostinger VPS, Apify's
LinkedIn scraper, OpenAI/Anthropic, and Telegram - most of which cost money
pretty quickly. I rebuilt the same idea but swapped almost every piece for
something free, and used WhatsApp instead of Telegram since that's what I
actually check throughout the day. Below is what's different and why.

## What it actually does

1. Every morning, pull fresh job postings for keywords I care about
2. Skip anything already seen before (checked against a database)
3. Ask an LLM to score each new one against my resume, 1-10, with a reason
4. Message me the best ones on WhatsApp, with "Interested" / "Skip" buttons
5. When I tap a button, log that decision so there's a record of what I did

That's basically it. No auto-apply, no auto-generated cover letters getting
fired off without me looking - I still make every actual decision, the agent
just does the tedious filtering part.

## Why it's (mostly) free instead of following the article exactly

| Piece | Article's approach | What I used instead | Why |
|---|---|---|---|
| Job data | Apify's LinkedIn scraper | [Remotive](https://remotive.com/api/remote-jobs) + [RemoteOK](https://remoteok.com/api) APIs | Both are free with no signup, and scraping LinkedIn directly is against their ToS. Coverage isn't 100% identical to LinkedIn but it's decent. |
| LLM | OpenAI / Anthropic (needs a card) | [Groq](https://console.groq.com) | Free API key, no card, and fast |
| Daily scan | Hostinger VPS (~$5/mo, always on) | GitHub Actions cron | Free on a public repo. No server sitting around 24/7 for something that only needs to run once a day. |
| Messaging | Telegram | WhatsApp (Meta Cloud API) | Wanted this on WhatsApp since that's where I actually look. Free tier, but see the trade-off below. |
| Reply handling | Telegram gateway on the VPS | Small Flask webhook on Render's free tier | Explained below - this is the one part that isn't 100% serverless anymore. |
| Database | Supabase | Supabase (same) | Their free tier is genuinely free, no changes needed here |

End result: this still costs $0/month to run. The trade-off for using
WhatsApp is explained below.

## The one wrinkle: WhatsApp needs a webhook, not a poll

Telegram lets a bot just ask "anything new for me?" whenever it feels like it
(that's how the original design + my first draft of this worked). WhatsApp's
Cloud API doesn't work that way - it pushes button taps to a URL you
register with Meta, and that URL has to be up and listening whenever someone
might tap a button, not just once a day.

So this project has one small always-on-ish piece: `job_hunter/webhook.py`,
a tiny Flask app deployed to Render's free web service tier. Everything else
(the actual daily job search) is still a GitHub Actions cron job with no
server involved. Render's free tier does spin the service down after 15
minutes of no traffic and takes 30-60 seconds to wake back up on the next
request - Meta retries failed webhook deliveries for a while, so a button
tap that lands while the service is asleep should still eventually go
through, just not instantly.

## How it's put together

```
daily_scan.yml (github actions cron, once a day)
  -> fetch_jobs.py     pulls postings from Remotive + RemoteOK
  -> db.py              checks which ones are new
  -> score_jobs.py      asks Groq to score the new ones against my resume
  -> db.py              saves every scored job (so we don't re-score it tomorrow)
  -> notify.py          whatsapps me the top matches with Interested/Skip buttons

webhook.py (small Flask app, deployed on Render, always listening)
  -> receives the button tap from Meta's servers
  -> db.py              marks that job as interested/skipped
```

## Setup

### 1. WhatsApp (Meta Cloud API)
- Go to [developers.facebook.com](https://developers.facebook.com), create an app, add the "WhatsApp" product
- Meta gives you a free test phone number to start - grab its **phone number ID** and a **temporary access token** from the WhatsApp > API Setup page (you can generate a permanent token later under System Users, but the temporary one is fine to get started)
- Add your own phone number as a recipient under "To" in that same API Setup page (in developer mode you can only message verified numbers)
- Message that test number from your own WhatsApp first - Meta requires the user to message the business first (or within the last 24h) before it'll deliver a normal message to them
- Make up your own random string for `WHATSAPP_VERIFY_TOKEN` (you'll enter this same value on Meta's side later, it's just a shared secret so Meta knows it's really you registering the webhook)

### 2. Groq
- Sign up at [console.groq.com](https://console.groq.com) (free, no card)
- Create an API key

### 3. Supabase
- New project at [supabase.com](https://supabase.com) (free tier)
- Open the SQL editor, paste in `supabase_schema.sql`, run it
- Grab your project URL and the `service_role` key from Project Settings > API

### 4. Deploy the webhook to Render
- New Web Service on [render.com](https://render.com), point it at this repo, it'll pick up `render.yaml` + the `Dockerfile` automatically
- Add the env vars it asks for (`WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TO_NUMBER`, `WHATSAPP_VERIFY_TOKEN`, `SUPABASE_URL`, `SUPABASE_KEY`)
- Once it's deployed, go back to Meta's WhatsApp > Configuration page and set the webhook URL to `https://<your-render-url>/webhook`, with the verify token you made up above. Subscribe to the `messages` field.

### 5. Wire up GitHub secrets for the daily scan

```
gh secret set GROQ_API_KEY
gh secret set WHATSAPP_TOKEN
gh secret set WHATSAPP_PHONE_NUMBER_ID
gh secret set WHATSAPP_TO_NUMBER
gh secret set SUPABASE_URL
gh secret set SUPABASE_KEY
gh secret set RESUME_TEXT < resume/resume.txt
```

And a couple of non-secret repo variables for your search:

```
gh variable set SEARCH_KEYWORDS --body "forward deployed engineer,solutions engineer"
gh variable set SEARCH_LOCATION --body "remote"
```

### 6. Test it
Trigger the scan manually instead of waiting for the cron:

```
gh workflow run daily_scan.yml
```

Then check the Actions tab for logs, and your WhatsApp for messages. Tap a
button and check the Render logs / your Supabase `decisions` table to make
sure the reply made it through.

## Running locally

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill it in
export $(cat .env | xargs)
python -m job_hunter.main       # runs one scan
python -m job_hunter.webhook    # runs the webhook locally on :8080 (use ngrok or similar to expose it to Meta for local testing)
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
- The webhook lives on Render's free tier, which sleeps after 15 minutes
  idle. A button tap while it's asleep isn't lost, just delayed until Meta's
  retry (or the next tap) wakes it back up.
- Meta's test WhatsApp number only works with phone numbers you've manually
  verified in the developer console, so this is really built for personal
  use, not something you'd hand to someone else as-is.

## About this project

This is one of a handful of projects I built to demonstrate the kind of
end-to-end ownership a Forward Deployed Engineer role needs - scoping a
problem, picking pragmatic (and cheap) tools, and shipping something that
actually works day to day, not just a demo.
