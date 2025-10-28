#!/bin/bash
set -euo pipefail

############################################
#              CONFIGURAZIONE              #
############################################
# >>> Modifica questi valori <<<
RUNTIME="python3.11"                     # Deve coincidere con la tua Lambda
PLATFORM="linux/amd64"                   # Architettura x86_64
IMAGE="public.ecr.aws/lambda/python:${RUNTIME#python}" # Immagine runtime Lambda
OUTPUT_DIR="./build"
OUTPUT_ZIP="psycopg2-layer.zip"
PKGS=("psycopg2-binary==2.9.9" "requests" "boto3")     # Pacchetti da includere

############################################
#           CONTROLLI PREREQUISITI         #
############################################
echo "==> Verifica prerequisiti"
command -v podman >/dev/null || { echo "ERRORE: podman non trovato"; exit 1; }
command -v unzip >/dev/null || { echo "ERRORE: unzip non trovato"; exit 1; }

############################################
#              BUILD DEL LAYER             #
############################################
echo "==> Pulizia cartella build"
rm -rf "$OUTPUT_DIR" && mkdir -p "$OUTPUT_DIR"

PKG_STR="${PKGS[*]}"
echo "Pacchetti da installare: $PKG_STR"
echo "Immagine runtime Lambda: $IMAGE (piattaforma: $PLATFORM)"

podman run --rm -it --platform "$PLATFORM" \
  --entrypoint bash \
  -v "$PWD/$OUTPUT_DIR":/opt/build \
  "$IMAGE" \
  -lc "set -euxo pipefail
# Mostra info Python/pip
python --version
pip --version

# zip non sempre presente; installiamolo se manca
command -v zip >/dev/null || (yum install -y zip || microdnf install -y zip || true)

# 1) Struttura layer
mkdir -p /opt/build/python

# 2) Installa pacchetti nel path corretto
pip install --no-cache-dir $PKG_STR -t /opt/build/python

# 3) Verifica import e versioni
python - <<'PY'
import psycopg2, requests, boto3
print('Python OK:', psycopg2.__version__, requests.__version__, boto3.__version__)
PY

# 4) Mostra architettura del modulo nativo
file /opt/build/python/psycopg2/_psycopg*.so || true

# 5) Crea lo ZIP con 'python/' in root
cd /opt/build
zip -r $OUTPUT_ZIP python
"

############################################
#            VERIFICHE LOCALI              #
############################################
echo "==> Controllo ZIP"
unzip -l "$OUTPUT_DIR/$OUTPUT_ZIP" | head -n 20

echo "==> Controllo binario psycopg2"
file "$OUTPUT_DIR/python/psycopg2/_psycopg"*.so || true

echo "==> Layer pronto in: $OUTPUT_DIR/$OUTPUT_ZIP"