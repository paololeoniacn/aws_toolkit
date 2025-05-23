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

cleanup() {
  info "Rimuovo il file temporaneo .env"
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
      echo "Esempio: $0 -env prod -- --since 1h --filter utility"
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


# Reimposta gli argomenti posizionali finali
if [ ${#POSITIONAL_ARGS[@]} -gt 0 ]; then
  set -- "${POSITIONAL_ARGS[@]}"
else
  set --
fi


# ---------------------------------------------------
# 1. Controlla che podman sia installato
# ---------------------------------------------------
if ! command -v podman >/dev/null 2>&1; then
  error_exit "podman non trovato. Installa Podman seguendo https://podman.io/getting-started/installation"
fi

# ---------------------------------------------------
# 2. Verifica presenza file .env (dinamico)
# ---------------------------------------------------
ENV_FILE=".env"
if [ -n "$ENV_SUFFIX" ]; then
  ENV_FILE=".env.${ENV_SUFFIX}"
else 
  ENV_FILE=".env.dev"
fi

info "Usando file di ambiente: ${ENV_FILE}"
cp "$ENV_FILE" "$TARGET_FILE"

if [ ! -f "$TARGET_FILE" ]; then
  error_exit "file '$ENV_FILE' non trovato. Crea '$ENV_FILE' con le variabili d'ambiente necessarie prima di eseguire lo script."
fi

# ---------------------------------------------------
# 3. Configurazione immagine
# ---------------------------------------------------
IMAGE_NAME="cloudwatch-tail"

# ---------------------------------------------------
# 4. Costruzione immagine
# ---------------------------------------------------
info "Inizio build dell'immagine '$IMAGE_NAME'..."
if ! podman build -t "$IMAGE_NAME" .; then
  error_exit "build fallita. Controlla il Dockerfile e i permessi nella directory corrente."
fi
info "Build completata con successo."

# ---------------------------------------------------
# 5. Avvio del container
# ---------------------------------------------------
if [ $# -eq 0 ]; then
  info "Nessun argomento passato al container."
fi

info "Avvio del container '$IMAGE_NAME'..."
if ! podman run --rm -it \
    --env-file "$TARGET_FILE" \
    "$IMAGE_NAME" "$@"; then
  error_exit "avvio del container fallito. 
- Verifica i parametri passati: $* 
- Controlla il contenuto di '$TARGET_FILE' 
- Assicurati che l’immagine esista con 'podman images'"
fi

info "Container terminato correttamente."
