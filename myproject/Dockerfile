FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential default-libmysqlclient-dev pkg-config libffi-dev libssl-dev \
 && rm -rf /var/lib/apt/lists/*

ARG REQ_FILE=requirements.txt
COPY ${REQ_FILE} /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

CMD ["python", "myproject/manage.py", "runserver", "0.0.0.0:8000"]
