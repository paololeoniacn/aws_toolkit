#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------
# Funzioni di supporto
# ---------------------------------------------------
error_exit() {
  echo "❌ Errore: $1" >&2
  exit "${2:-1}"
}

info() {
  echo "ℹ️  $1"
}

cleanup() {
  info "Pulizia file temporaneo .env"
  rm -f .env
}

trap cleanup EXIT INT TERM

# ---------------------------------------------------
# Parsing argomenti
# ---------------------------------------------------
ENV_SUFFIX=""
POSITIONAL_ARGS=()
TARGET_FILE=".env"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -env|--env)
      ENV_SUFFIX="$2"
      shift 2
      ;;
    -h|--help)
      echo "Uso: $0 [-env <ambiente>] -- [argomenti da passare al container]"
      echo "Esempio: $0 -env prod -- --limit 20"
      exit 0
      ;;
    --)
      shift
      POSITIONAL_ARGS+=("$@")
      break
      ;;
    -*)
      error_exit "Opzione sconosciuta: $1"
      ;;
    *)
      POSITIONAL_ARGS+=("$1")
      shift
      ;;
  esac
done

# Imposta argomenti finali
if [ ${#POSITIONAL_ARGS[@]} -gt 0 ]; then
  set -- "${POSITIONAL_ARGS[@]}"
else
  set --
fi

# ---------------------------------------------------
# 1. Verifica Podman
# ---------------------------------------------------
if ! command -v podman >/dev/null 2>&1; then
  error_exit "Podman non è installato. Installa da https://podman.io/getting-started/installation"
fi

# ---------------------------------------------------
# 2. Selezione file .env
# ---------------------------------------------------
if [ -n "$ENV_SUFFIX" ]; then
  ENV_FILE=".env.${ENV_SUFFIX}"
else
  ENV_FILE=".env.dev"
fi

info "Uso file ambiente: $ENV_FILE"
cp "$ENV_FILE" "$TARGET_FILE"

if [ ! -f "$TARGET_FILE" ]; then
  error_exit "File '$ENV_FILE' non trovato. Creane uno con le variabili necessarie."
fi

# ---------------------------------------------------
# 3. Nome immagine
# ---------------------------------------------------
IMAGE_NAME="log-monitor"

# ---------------------------------------------------
# 4. Build immagine
# ---------------------------------------------------
info "Build immagine '$IMAGE_NAME'..."
if ! podman build -t "$IMAGE_NAME" .; then
  error_exit "Build fallita. Controlla il Dockerfile."
fi
info "Build completata."

# ---------------------------------------------------
# 5. Run container
# ---------------------------------------------------
info "Avvio container '$IMAGE_NAME'..."
LOG_DIR_HOST="$(pwd)/logs"
mkdir -p "$LOG_DIR_HOST"

if ! podman run --rm -it \
    --env-file "$TARGET_FILE" \
    -v "$LOG_DIR_HOST":/app/logs:Z \
    "$IMAGE_NAME" "$@"; then

  error_exit "Errore nell'avvio del container.
- Parametri: $*
- File .env usato: '$TARGET_FILE'
- Immagine presente? Usa 'podman images'"
fi

info "Esecuzione completata."
