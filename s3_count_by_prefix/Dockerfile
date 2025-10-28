# ---------------------------------------------------
# Base image
# ---------------------------------------------------
FROM python:3.11-slim

# Evita input interattivo e forza UTF-8
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ---------------------------------------------------
# Dipendenze di sistema minime
# ---------------------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       bash \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------
# Working directory
# ---------------------------------------------------
WORKDIR /app

# ---------------------------------------------------
# Requisiti Python
# ---------------------------------------------------
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------
# Copia codice sorgente
# ---------------------------------------------------
COPY . /app/

# ---------------------------------------------------
# Entry point: script di count
# ---------------------------------------------------
ENTRYPOINT ["python", "count_s3.py"]
