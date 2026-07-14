# reads all the settings from environment variables
# (github actions injects these from repo secrets, locally you'd use a .env file + python-dotenv)

import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

# whatsapp cloud api stuff - see README for how to get these from
# developers.facebook.com
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_TO_NUMBER = os.environ.get("WHATSAPP_TO_NUMBER", "")  # your own number, with country code, no +
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")  # made up by you, used when registering the webhook

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# comma separated, e.g. "forward deployed engineer,solutions engineer,site reliability engineer"
SEARCH_KEYWORDS = [k.strip() for k in os.environ.get("SEARCH_KEYWORDS", "forward deployed engineer").split(",") if k.strip()]
SEARCH_LOCATION = os.environ.get("SEARCH_LOCATION", "remote")

# don't bother telling me about anything below this score (out of 10)
MIN_SCORE = int(os.environ.get("MIN_SCORE", "6"))
TOP_N = int(os.environ.get("TOP_N", "5"))

# resume text - either passed straight in as an env var (that's what the github action does,
# pulling from a repo secret) or read from a local file when testing on your own machine
RESUME_PATH = os.environ.get("RESUME_PATH", "resume/resume.txt")


def get_resume_text():
    env_resume = os.environ.get("RESUME_TEXT")
    if env_resume:
        return env_resume

    if os.path.exists(RESUME_PATH):
        with open(RESUME_PATH, "r") as f:
            return f.read()

    # fall back to the sample so the project still runs for anyone who clones it
    with open("resume/resume.sample.txt", "r") as f:
        return f.read()
