# small flask app that just sits and waits for whatsapp to tell us about
# button taps. unlike telegram, whatsapp's cloud api won't let you poll for
# updates - it pushes them to a webhook url you register, so this one piece
# actually needs to stay running somewhere (deployed to render's free tier,
# see render.yaml / Dockerfile). everything else in this project is just a
# github actions cron job, this is the one exception.

from flask import Flask, request

from job_hunter import config, db

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health():
    # just so render's health check has something to hit that isn't the
    # actual webhook verification route (that one needs meta's specific
    # query params or it'll 403, which would make render think we're down)
    return "ok", 200


@app.route("/webhook", methods=["GET"])
def verify():
    # meta calls this once when you register the webhook url, just to make
    # sure you actually control the endpoint
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == config.WHATSAPP_VERIFY_TOKEN:
        return challenge, 200
    return "verification failed", 403


@app.route("/webhook", methods=["POST"])
def receive():
    payload = request.get_json(silent=True) or {}

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                _handle_message(message)

    # respond quickly either way - meta just wants a 200, it doesn't care
    # what's in the body
    return "ok", 200


def _handle_message(message):
    if message.get("type") != "interactive":
        return

    button_reply = message.get("interactive", {}).get("button_reply")
    if not button_reply:
        return

    action, _, job_id = button_reply["id"].partition(":")
    if action not in ("interested", "skip"):
        print(f"got a button id we don't recognize: {button_reply['id']}")
        return

    decision = db.find_pending_decision_by_job_id(job_id)
    if decision is None:
        print(f"no pending decision found for job {job_id}, ignoring")
        return

    status = "interested" if action == "interested" else "skipped"
    db.update_decision_status(decision["id"], status)
    print(f"job {job_id} marked as {status}")


if __name__ == "__main__":
    # just for local testing - render runs this through gunicorn instead
    app.run(port=8080)
