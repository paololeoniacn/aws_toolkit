#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------
# Funzioni di supporto
# ---------------------------------------------------
error_exit() {
  echo "Errore: $1" >&2
  exit "${2:-1}"
}

info() {
  echo "⟳ $1"
}

# ---------------------------------------------------
# 1. Controlla che podman sia installato
# ---------------------------------------------------
if ! command -v podman >/dev/null 2>&1; then
  error_exit "podman non trovato. Installa Podman seguendo https://podman.io/getting-started/installation"
fi

# ---------------------------------------------------
# 2. Verifica presenza file .env
# ---------------------------------------------------
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
  error_exit "file '$ENV_FILE' non trovato. Crea '$ENV_FILE' con le variabili d'ambiente necessarie prima di eseguire lo script."
fi

# ---------------------------------------------------
# Configurazione
# ---------------------------------------------------
IMAGE_NAME="cloudwatch-tail"

# ---------------------------------------------------
# 3. Costruzione dell’immagine
# ---------------------------------------------------
info "Inizio build dell'immagine '$IMAGE_NAME'..."
if ! podman build -t "$IMAGE_NAME" .; then
  error_exit "build fallita. Controlla il Dockerfile e i permessi nella directory corrente."
fi
info "Build completata con successo."

# ---------------------------------------------------
# 4. Avvio del container
# ---------------------------------------------------
info "Avvio del container '$IMAGE_NAME'..."
if ! podman run --rm -it \
    --env-file "$ENV_FILE" \
    "$IMAGE_NAME" "$@"; then
  error_exit "avvio del container fallito. 
- Verifica i parametri passati (\$@): $* 
- Controlla il contenuto di '$ENV_FILE' 
- Verificare se esistono log richiesti con parametri '$@' 
- Assicurati che l’immagine esista con 'podman images'."
fi

info "Container terminato correttamente."
