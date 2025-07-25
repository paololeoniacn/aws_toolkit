#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------
# Funzioni di supporto
# ---------------------------------------------------
info() {
  echo "⟳ $1"
}

warn() {
  echo "⚠ $1" >&2
}

# ---------------------------------------------------
# 1. Rimuovi immagine Podman
# ---------------------------------------------------
IMAGE_NAME="cloudwatch-tail"
if podman images --format "{{.Repository}}" | grep -q "^${IMAGE_NAME}$"; then
  info "Rimuovo immagine Podman '${IMAGE_NAME}'"
  podman rmi "${IMAGE_NAME}"
else
  warn "Immagine '${IMAGE_NAME}' non trovata -> IMAGE PRUNE"
  podman image prune 
fi

# ---------------------------------------------------
# 2. rimuovi eventuali container dangling
# ---------------------------------------------------
DANGLING_CONTAINERS=$(podman ps -a --filter "ancestor=${IMAGE_NAME}" --format "{{.ID}}")
if [ -n "$DANGLING_CONTAINERS" ]; then
  info "Rimuovo container residui basati su '${IMAGE_NAME}'"
  podman rm -f $DANGLING_CONTAINERS
fi

info "Clean completato."
