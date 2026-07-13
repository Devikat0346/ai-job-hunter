# sends job matches to telegram, with a couple of inline buttons so you can
# tap "interested" or "skip" right from the message instead of having to
# reply with text.

import requests

from job_hunter import config

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def send_job(job):
    text = (
        f"*{job['title']}*\n"
        f"{job['company']} — {job['location']}\n\n"
        f"Score: {job['score']}/10\n"
        f"{job['reason']}\n\n"
        f"_Tailoring tip: {job['tailor_notes']}_\n\n"
        f"[View posting]({job['url']})"
    )

    # callback_data has a 64 byte limit on telegram's side, so we just tag
    # the job's row id in supabase rather than trying to stuff more in there
    keyboard = {
        "inline_keyboard": [[
            {"text": "👍 Interested", "callback_data": f"interested:{job['db_id']}"},
            {"text": "👎 Skip", "callback_data": f"skip:{job['db_id']}"},
        ]]
    }

    resp = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "reply_markup": keyboard,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["result"]["message_id"]


def send_plain_message(text):
    resp = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text},
        timeout=15,
    )
    resp.raise_for_status()
