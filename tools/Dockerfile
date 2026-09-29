FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl jq git postgresql-client unzip \
  && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir boto3 psycopg2-binary pillow requests flask awscli
WORKDIR /trabajo
CMD ["sleep","infinity"]
