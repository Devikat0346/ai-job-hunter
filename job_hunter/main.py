# this is the daily job, github actions runs it every morning.
# grabs fresh postings, skips whatever we've already seen, scores the rest
# against the resume, whatsapps me the good ones.

from job_hunter import config, db, notify
from job_hunter.fetch_jobs import fetch_all_jobs
from job_hunter.score_jobs import score_jobs


def run():
    resume_text = config.get_resume_text()
    print(f"searching for: {', '.join(config.SEARCH_KEYWORDS)}")

    all_jobs = fetch_all_jobs(config.SEARCH_KEYWORDS)

    new_jobs = [j for j in all_jobs if not db.job_already_seen(j["url"])]
    print(f"{len(new_jobs)} of those are new (haven't seen the rest before)")

    if not new_jobs:
        print("nothing new today")
        return

    scored_jobs = score_jobs(resume_text, new_jobs)

    good_matches = [j for j in scored_jobs if j["score"] >= config.MIN_SCORE]
    top_jobs = good_matches[: config.TOP_N]

    # save every job we looked at today, not just the good ones, so we
    # don't re-score the same posting again tomorrow if it's still up
    for job in scored_jobs:
        saved = db.save_job(job)
        job["db_id"] = saved["id"]

    if not top_jobs:
        print(f"scored {len(scored_jobs)} new jobs, none cleared the min score of {config.MIN_SCORE}")
        return

    print(f"sending {len(top_jobs)} good matches over whatsapp")
    for job in top_jobs:
        message_id = notify.send_job(job)
        db.save_decision(job["db_id"], message_id)

    print("done")


if __name__ == "__main__":
    run()
