# just talking to supabase's REST api directly instead of installing their
# python package, didn't feel worth the extra dependency for a few http calls.
# using the service_role key here (not anon) since it's just me using this.

import requests

from job_hunter import config

HEADERS = {
    "apikey": config.SUPABASE_KEY,
    "Authorization": f"Bearer {config.SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def _url(path):
    return f"{config.SUPABASE_URL}/rest/v1/{path}"


def job_already_seen(job_url):
    resp = requests.get(
        _url("jobs"),
        headers=HEADERS,
        params={"url": f"eq.{job_url}", "select": "id"},
        timeout=15,
    )
    resp.raise_for_status()
    return len(resp.json()) > 0


def save_job(job):
    payload = {
        "source": job["source"],
        "job_id": job["job_id"],
        "title": job["title"],
        "company": job["company"],
        "location": job["location"],
        "url": job["url"],
        "score": job.get("score"),
        "reason": job.get("reason"),
        "tailor_notes": job.get("tailor_notes"),
    }
    resp = requests.post(
        _url("jobs"),
        headers={**HEADERS, "Prefer": "return=representation"},
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()[0]


def save_decision(job_id, whatsapp_message_id):
    payload = {
        "job_id": job_id,
        "whatsapp_message_id": whatsapp_message_id,
        "status": "pending",
    }
    resp = requests.post(
        _url("decisions"),
        headers={**HEADERS, "Prefer": "return=representation"},
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()[0]


def find_pending_decision_by_job_id(job_id):
    # the whatsapp button reply hands us the job id directly (see notify.py),
    # so we don't need to look anything up by message id the way the old
    # telegram version had to
    resp = requests.get(
        _url("decisions"),
        headers=HEADERS,
        params={"job_id": f"eq.{job_id}", "status": "eq.pending", "select": "*"},
        timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def update_decision_status(decision_id, status):
    resp = requests.patch(
        _url("decisions"),
        headers=HEADERS,
        params={"id": f"eq.{decision_id}"},
        json={"status": status},
        timeout=15,
    )
    resp.raise_for_status()
