# Usa un'immagine Python leggera
FROM python:3.11-slim

# Imposta directory di lavoro
WORKDIR /app

# Copia i file del progetto
COPY . .

# Installa dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Imposta comando di default
CMD ["python", "get_falso_positivi.py"]
