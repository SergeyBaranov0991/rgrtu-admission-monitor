FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY certs/*.pem /usr/local/share/ca-certificates/
RUN for cert in /usr/local/share/ca-certificates/*.pem; do cp "$cert" "${cert%.pem}.crt"; done \
    && update-ca-certificates

COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
COPY tests/fixtures ./tests/fixtures

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
