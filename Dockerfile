FROM python:3.12-slim

WORKDIR /app

COPY meetingpulse/pyproject.toml .

RUN pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir \
        fastmcp \
        apscheduler \
        sqlalchemy \
        google-api-python-client \
        google-auth-oauthlib \
        httpx \
        python-dotenv \
        dateparser

COPY meetingpulse/ .

EXPOSE 8000

CMD ["python", "server.py"]
