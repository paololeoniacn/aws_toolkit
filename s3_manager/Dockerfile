# Immagine base Python leggera
FROM python:3.11-slim

# Evita output interattivo di pip
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# Crea workdir
WORKDIR /app

# Copia requirements e installa
COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r /app/requirements.txt

# Copia il codice applicativo
COPY s3_manager.py /app/s3_manager.py

# Comando di default
CMD ["python3", "s3_manager.py"]
