# sends job matches over whatsapp (meta's cloud api), with interested/skip
# buttons baked into the message. whatsapp's formatting is close enough to
# telegram's - *bold* and _italic_ both work, it just doesn't do markdown
# links, so the url is just plain text and whatsapp auto-links it itself.

import requests

from job_hunter import config

GRAPH_API = f"https://graph.facebook.com/v20.0/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"


def _headers():
    return {
        "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }


def send_job(job):
    body_text = (
        f"*{job['title']}*\n"
        f"{job['company']} — {job['location']}\n\n"
        f"Score: {job['score']}/10\n"
        f"{job['reason']}\n\n"
        f"_Tailoring tip: {job['tailor_notes']}_\n\n"
        f"{job['url']}"
    )

    # whatsapp only allows 3 reply buttons max, we just need 2. the button
    # id is what we get back in the webhook when it's tapped, so we tag the
    # job's supabase row id directly onto it - saves having to look anything
    # up by message id like the telegram version needed to
    payload = {
        "messaging_product": "whatsapp",
        "to": config.WHATSAPP_TO_NUMBER,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": f"interested:{job['db_id']}", "title": "👍 Interested"}},
                    {"type": "reply", "reply": {"id": f"skip:{job['db_id']}", "title": "👎 Skip"}},
                ]
            },
        },
    }

    resp = requests.post(GRAPH_API, headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()["messages"][0]["id"]


def send_plain_message(text):
    payload = {
        "messaging_product": "whatsapp",
        "to": config.WHATSAPP_TO_NUMBER,
        "type": "text",
        "text": {"body": text},
    }
    resp = requests.post(GRAPH_API, headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
