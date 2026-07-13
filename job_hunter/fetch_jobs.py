# pulls job postings from a couple of free, no-signup-needed job boards.
# started with just Remotive but added RemoteOK too since Remotive alone
# was pretty thin some days. both are just plain JSON over http, no auth.

import requests

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
REMOTEOK_URL = "https://remoteok.com/api"


def fetch_from_remotive(keywords):
    jobs = []
    for kw in keywords:
        try:
            resp = requests.get(REMOTIVE_URL, params={"search": kw}, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"remotive request failed for '{kw}': {e}")
            continue

        data = resp.json()
        for job in data.get("jobs", []):
            jobs.append({
                "source": "remotive",
                "job_id": str(job.get("id")),
                "title": job.get("title", "").strip(),
                "company": job.get("company_name", "").strip(),
                "location": job.get("candidate_required_location", ""),
                "url": job.get("url", ""),
                "description": job.get("description", ""),
                "posted_at": job.get("publication_date", ""),
            })
    return jobs


def fetch_from_remoteok(keywords):
    # remoteok doesn't support a search param, so we just grab the firehose
    # and filter locally by keyword match on title/tags
    try:
        resp = requests.get(REMOTEOK_URL, timeout=15, headers={"User-Agent": "job-hunter-bot"})
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"remoteok request failed: {e}")
        return []

    data = resp.json()
    # first item in the response is just legal/meta info, not a real job
    listings = data[1:] if len(data) > 1 else []

    keywords_lower = [k.lower() for k in keywords]
    jobs = []
    for job in listings:
        title = (job.get("position") or job.get("title") or "").strip()
        tags = " ".join(job.get("tags", [])).lower()
        haystack = f"{title.lower()} {tags}"

        if not any(kw in haystack for kw in keywords_lower):
            continue

        jobs.append({
            "source": "remoteok",
            "job_id": str(job.get("id", job.get("slug", ""))),
            "title": title,
            "company": job.get("company", "").strip(),
            "location": job.get("location", "remote") or "remote",
            "url": job.get("url", ""),
            "description": job.get("description", ""),
            "posted_at": job.get("date", ""),
        })
    return jobs


def fetch_all_jobs(keywords):
    jobs = fetch_from_remotive(keywords) + fetch_from_remoteok(keywords)

    # dedupe within this batch by url, in case both sources return the same posting
    seen_urls = set()
    unique_jobs = []
    for job in jobs:
        if job["url"] in seen_urls:
            continue
        seen_urls.add(job["url"])
        unique_jobs.append(job)

    print(f"fetched {len(unique_jobs)} unique jobs across {len(keywords)} keyword(s)")
    return unique_jobs
