# this is the piece that closes the loop: it checks telegram for any button
# taps since last time (interested / skip) and writes the decision back into
# supabase. runs on its own github actions schedule every 15 minutes, totally
# separate from the daily job scan.
#
# telegram's getUpdates needs an "offset" so it doesn't hand you the same
# updates over and over. since github actions doesn't keep any state between
# runs, we stash the last update id we've seen in supabase itself (a one-row
# table, see supabase_schema.sql) instead of a local file.

import requests

from job_hunter import config, db

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def get_last_update_id():
    resp = requests.get(
        f"{config.SUPABASE_URL}/rest/v1/bot_state",
        headers=db.HEADERS,
        params={"id": "eq.1", "select": "last_update_id"},
        timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0]["last_update_id"] if rows else None


def set_last_update_id(update_id):
    requests.patch(
        f"{config.SUPABASE_URL}/rest/v1/bot_state",
        headers=db.HEADERS,
        params={"id": "eq.1"},
        json={"last_update_id": update_id},
        timeout=15,
    ).raise_for_status()


def answer_callback(callback_query_id, text):
    requests.post(
        f"{TELEGRAM_API}/answerCallbackQuery",
        json={"callback_query_id": callback_query_id, "text": text},
        timeout=15,
    )


def process_updates():
    last_id = get_last_update_id()
    params = {"timeout": 0}
    if last_id is not None:
        params["offset"] = last_id + 1

    resp = requests.get(f"{TELEGRAM_API}/getUpdates", params=params, timeout=20)
    resp.raise_for_status()
    updates = resp.json().get("result", [])

    if not updates:
        print("no new telegram updates")
        return

    highest_seen = last_id or 0

    for update in updates:
        highest_seen = max(highest_seen, update["update_id"])

        callback = update.get("callback_query")
        if not callback:
            continue

        action, _, decision_id = callback["data"].partition(":")
        decision = None
        # decisions were saved keyed by telegram message id when we sent the job,
        # but the button data carries the job's db id - look it up by message id instead
        message_id = callback["message"]["message_id"]
        decision = db.find_pending_decision(message_id)

        if decision is None:
            print(f"no matching decision found for message {message_id}, skipping")
            answer_callback(callback["id"], "Hmm, couldn't find that job in the database.")
            continue

        status = "interested" if action == "interested" else "skipped"
        db.update_decision_status(decision["id"], status)
        answer_callback(callback["id"], f"Marked as {status}!")
        print(f"decision {decision['id']} -> {status}")

    set_last_update_id(highest_seen)


if __name__ == "__main__":
    process_updates()
