#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------
# Funzioni
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
  rm -f .env || true
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
      echo "Esempi:"
      echo "  $0 -env prod -- --bucket my-bucket --prefix path/ --suffix .gz"
      echo "  $0 -- --bucket my-bucket --prefix data/"
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
# 1. Verifica Podman
# ---------------------------------------------------
command -v podman >/dev/null 2>&1 || \
  error_exit "podman non trovato. Installa Podman: https://podman.io/getting-started/installation"

# ---------------------------------------------------
# 2. Selezione file .env
# ---------------------------------------------------
ENV_FILE=".env.dev"
[ -n "$ENV_SUFFIX" ] && ENV_FILE=".env.${ENV_SUFFIX}"

info "Usando file di ambiente: ${ENV_FILE}"

if [ ! -f "$ENV_FILE" ]; then
  error_exit "file '$ENV_FILE' non trovato. Crealo con le variabili richieste (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION, S3_BUCKET, S3_PREFIX)."
fi

cp "$ENV_FILE" "$TARGET_FILE"

# ---------------------------------------------------
# 3. Config immagine
# ---------------------------------------------------
IMAGE_NAME="s3-counter"

# ---------------------------------------------------
# 4. Build immagine
# ---------------------------------------------------
info "Build dell'immagine '$IMAGE_NAME'..."
podman build -t "$IMAGE_NAME" .
info "Build completata."

# ---------------------------------------------------
# 5. Run container
# ---------------------------------------------------
if [ $# -eq 0 ]; then
  info "Nessun argomento passato al container. Il container userà le variabili .env."
fi

info "Avvio del container '$IMAGE_NAME'..."
# Nota: si assume che il Dockerfile imposti l'ENTRYPOINT sullo script Python (es. count_s3.py)
if ! podman run --rm -it \
    --env-file "$TARGET_FILE" \
    "$IMAGE_NAME" "$@"; then
  error_exit "avvio del container fallito.
- Verifica i parametri: $*
- Controlla '$TARGET_FILE'
- Controlla l'immagine con 'podman images'"
fi

info "Container terminato correttamente."
