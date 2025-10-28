# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rename_segment.py .

# Default env file (può essere sovrascritto)
COPY .env .

# Punto di ingresso
ENTRYPOINT ["python", "rename_segment.py"]
