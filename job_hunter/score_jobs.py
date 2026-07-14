# asks groq's llama model to rate each job against your resume.
# groq's api is openai-compatible so this is basically the same shape of
# request you'd send to openai, just a different base url + free key.

import json
import re
import requests

from job_hunter import config

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

PROMPT_TEMPLATE = """You are helping someone screen job postings against their resume.

RESUME:
{resume}

TARGET ROLES / KEYWORDS THEY CARE ABOUT:
{keywords}

JOB POSTING:
Title: {title}
Company: {company}
Location: {location}
Description:
{description}

Rate how good a fit this job is for this specific person on a scale of 1-10
(10 = should apply today, 1 = not even close). Base it on their actual
resume, not just keyword overlap in the title. Then write one short sentence
explaining the score, and one short sentence of tailoring advice (what to
emphasize on their resume/cover letter for this posting - do NOT invent
experience they don't have).

Respond with ONLY valid JSON, no other text, in exactly this shape:
{{"score": <integer 1-10>, "reason": "<one sentence>", "tailor_notes": "<one sentence>"}}
"""


def score_job(resume_text, job):
    # descriptions from these job boards can be pretty long / full of html,
    # truncating keeps the prompt (and the free-tier token usage) reasonable
    description = job["description"][:3000]

    prompt = PROMPT_TEMPLATE.format(
        resume=resume_text,
        keywords=", ".join(config.SEARCH_KEYWORDS),
        title=job["title"],
        company=job["company"],
        location=job["location"],
        description=description,
    )

    resp = requests.post(
        GROQ_CHAT_URL,
        headers={
            "Authorization": f"Bearer {config.GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        },
        timeout=30,
    )
    resp.raise_for_status()
    raw_text = resp.json()["choices"][0]["message"]["content"]

    return _parse_score_response(raw_text)


def _parse_score_response(raw_text):
    # sometimes it wraps the json in a sentence anyway even though i told it not to,
    # so just grab the first {...} looking chunk instead of trusting the whole reply
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        print(f"couldn't find json in model response: {raw_text!r}")
        return {"score": 0, "reason": "model gave a bad response", "tailor_notes": ""}

    try:
        result = json.loads(match.group(0))
    except json.JSONDecodeError:
        print(f"couldn't parse json from model response: {raw_text!r}")
        return {"score": 0, "reason": "model gave a bad response", "tailor_notes": ""}

    result["score"] = int(result.get("score", 0))
    return result


def score_jobs(resume_text, jobs):
    scored = []
    for job in jobs:
        try:
            result = score_job(resume_text, job)
        except requests.RequestException as e:
            print(f"scoring failed for '{job['title']}': {e}")
            continue

        job_with_score = {**job, **result}
        scored.append(job_with_score)

    scored.sort(key=lambda j: j["score"], reverse=True)
    return scored
