#!/bin/bash
set -euo pipefail


# ===== CONFIGURAZIONE =====
ACN_S3_LINK="https://of-test-smhub-fibercop.s3.eu-south-1.amazonaws.com/layer-lambda"
ACN_S3_REGION="eu-south-1"
BUCKET="of-test-smhub-fibercop"            # Bucket S3
KEY="layer-lambda"                       # Path nello S3
RUNTIME="python3.11"                    # Runtime Lambda
IMAGE="public.ecr.aws/lambda/python:${RUNTIME#python}" # Immagine Docker runtime Lambda
PLATFORM="linux/amd64"                  # Architettura x86_64
PKGS="psycopg2-binary requests boto3"   # Pacchetti da includere

echo "=== Pulizia cartella build ==="
rm -rf build && mkdir -p build

echo "=== Avvio container Docker per build layer ==="
docker run --rm -it --platform "$PLATFORM" \
  --entrypoint bash \
  -v "$PWD/build":/opt/build \
  "$IMAGE" \
  -lc "
set -euxo pipefail
yum install -y zip
mkdir -p /opt/build/python
pip install $PKGS -t /opt/build/python
python - <<PY
import psycopg2, requests, boto3
print('Python OK:', psycopg2.__version__, requests.__version__, boto3.__version__)
PY
file /opt/build/python/psycopg2/_psycopg*.so || true
cd /opt/build && zip -r psycopg2-layer.zip python
"

echo "=== Controllo ZIP ==="
unzip -l build/psycopg2-layer.zip | head -n 20

echo "=== Caricamento su S3 ==="
aws s3 cp build/psycopg2-layer.zip "s3://${BUCKET}/${KEY}"
aws s3 ls "s3://${BUCKET}/${KEY}"

echo "=== URL del file ==="
echo "https://s3.console.aws.amazon.com/s3/object/${BUCKET}?prefix=${KEY}"