FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    git-annex \
    datalad \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN chmod +x /app/deploy/docker/scripts/backend-entrypoint.sh && \
    chmod +x /app/deploy/docker/scripts/init-ria.sh && \
    chmod +x /app/deploy/docker/scripts/smoke-test.sh

EXPOSE 8000

CMD ["/app/deploy/docker/scripts/backend-entrypoint.sh"]