FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# render sets $PORT for us, gunicorn just needs to bind to it
CMD gunicorn --bind 0.0.0.0:$PORT job_hunter.webhook:app
