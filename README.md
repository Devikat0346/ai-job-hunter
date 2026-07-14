# ai-job-hunter

Small script that checks job boards every morning, scores whatever's new
against my resume, and messages me the good ones on whatsapp so I don't have
to sit there scrolling LinkedIn/Indeed every day. I'm job hunting for
Forward Deployed Engineer type roles right now and this has actually saved
me a decent amount of time.

Got the idea from [this substack post](https://abhijayvuyyuru.substack.com/p/build-your-own-ai-job-hunting-agent)
about building basically the same thing. Their version uses a Hostinger VPS,
Apify to scrape LinkedIn, OpenAI, and Telegram. I didn't want to pay for any
of that (also pretty sure scraping LinkedIn directly isn't allowed), so I
swapped almost everything for free stuff, and used WhatsApp instead of
Telegram since that's what I actually have open all day.

## what it does

- pulls fresh postings every morning from Remotive + RemoteOK (both free, no api key needed)
- skips anything it's already shown me before (tracked in a supabase table)
- sends new ones to an LLM (Groq, free) along with my resume, gets back a 1-10 score + why
- whatsapps me the top ~5, each with an Interested / Skip button
- tapping a button logs my decision back to the database

it does NOT auto-apply to anything or write cover letters for me. I still
look at every job myself and decide - it just cuts down the pile to look
through in the first place.

## the annoying part - whatsapp needs a webhook

Telegram lets your bot just ask "anything new?" whenever, which is how I
originally built the reply-listening bit (and matches the original article).
WhatsApp's Cloud API doesn't do that - Meta pushes button taps to a URL you
register with them, and that url has to be reachable whenever someone might
tap something, not just once a day.

So there's one small piece of this that isn't a github actions cron job:
`job_hunter/webhook.py`, a tiny flask app sitting on Render's free tier,
just waiting for Meta to POST to it. Render's free tier falls asleep after
15 min with no traffic and takes ~30-60 sec to wake up, so if I tap a button
right when it's asleep, it might take a bit to register. Meta retries failed
deliveries so it's not like the tap gets lost, just delayed sometimes.

Everything else - the actual daily job search part - is still just a
scheduled github action, no server needed.

## layout

```
job_hunter/
  fetch_jobs.py     - hits remotive + remoteok apis
  score_jobs.py      - sends jobs + resume to groq, gets back a score
  notify.py           - sends the whatsapp message w/ buttons
  webhook.py          - flask app, listens for button taps (deployed on render)
  db.py               - all the supabase read/write calls
  main.py             - ties fetch -> score -> notify together, this is what the cron runs
  config.py           - reads all the env vars / secrets

.github/workflows/daily_scan.yml   - the actual cron schedule
supabase_schema.sql                 - run this once when setting up a new supabase project
render.yaml / Dockerfile            - for deploying webhook.py
```

## setting it up

**Whatsapp (Meta cloud api)**
- make an app at developers.facebook.com, add the WhatsApp product
- meta gives you a free test number - copy its phone number id + a temporary token from API Setup
- add your own number under "To" in that same page (test numbers can only message verified recipients)
- send that test number a message from your own phone first - meta won't deliver to you otherwise until you've messaged them within the last 24h
- pick any random string for a verify token, you'll use it again when setting up the webhook

**Groq** - sign up at console.groq.com, free, no card, grab an api key

**Supabase** - new project (free tier), open the SQL editor and run `supabase_schema.sql`, then grab the project url + service_role key from settings

**Render** - new web service pointed at this repo, it'll find the render.yaml/Dockerfile on its own, just fill in the env vars it asks for. once it's live, go back to meta's WhatsApp > Configuration page, set the webhook url to `https://<your-render-app>/webhook` with the verify token from above, subscribe to `messages`.

**Github secrets** for the daily scan:
```
gh secret set GROQ_API_KEY
gh secret set WHATSAPP_TOKEN
gh secret set WHATSAPP_PHONE_NUMBER_ID
gh secret set WHATSAPP_TO_NUMBER
gh secret set SUPABASE_URL
gh secret set SUPABASE_KEY
gh secret set RESUME_TEXT < resume/resume.txt
```

and the search settings (not secret, just repo variables):
```
gh variable set SEARCH_KEYWORDS --body "forward deployed engineer,solutions engineer"
gh variable set SEARCH_LOCATION --body "remote"
```

then trigger it manually to test instead of waiting for the actual schedule:
```
gh workflow run daily_scan.yml
```

## running it on your own machine

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # fill in your own values
export $(cat .env | xargs)
python -m job_hunter.main      # runs one scan right now
python -m job_hunter.webhook   # runs the webhook locally, port 8080
```

## stuff that's not perfect

Remotive/RemoteOK don't have as much coverage as actually scraping LinkedIn
would, they lean pretty remote/tech-heavy. Scoring is only as good as the job
description text - some postings barely say anything and get scored low even
if they'd probably be fine. It doesn't rewrite your resume for each job, just
gives a one-line suggestion, since I didn't trust an LLM not to make up
experience I don't actually have if I let it fully rewrite things. And the
render free tier sleep thing means button taps aren't always instant.

Put my own resume in as a github secret rather than committing it to the
repo - `resume/resume.sample.txt` is just a placeholder so the project still
runs if someone else clones it.
