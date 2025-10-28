#!/usr/bin/env bash
# run_podman.sh
set -euo pipefail

# Carica variabili da .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

IMAGE_NAME="s3-multireplace"

# Build immagine se non esiste
if ! podman image exists "$IMAGE_NAME"; then
    echo "Costruisco immagine $IMAGE_NAME..."
    podman build -t "$IMAGE_NAME" .
fi

# Esegui container
podman run --rm \
    --name s3-rename \
    --env AWS_REGION \
    --env AWS_ACCESS_KEY_ID \
    --env AWS_SECRET_ACCESS_KEY \
    --env AWS_DEFAULT_OUTPUT \
    --env BUCKET \
    --env OLD_SEGMENT \
    --env NEW_SEGMENT \
    --env SEARCH_PREFIX \
    --env DRY_RUN \
    --env MAX_WORKERS \
    --env ALLOW_COLLISIONS \
    "$IMAGE_NAME"
