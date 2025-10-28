#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="s3-manager-img"
CONTAINER_NAME="s3-manager"
WORKDIR="/app"

echo "[INFO] build immagine ${IMAGE_NAME}"
podman build -t "${IMAGE_NAME}" .

echo "[INFO] cleanup container vecchio (se esiste)"
if podman ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}\$"; then
    podman rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
fi

echo "[INFO] run container interattivo"
podman run \
    --name "${CONTAINER_NAME}" \
    --env-file .env \
    -it \
    --workdir "${WORKDIR}" \
    "${IMAGE_NAME}"
