#!/bin/bash

VENV_DIR=".venv_monitor"

if [ ! -d "$VENV_DIR" ]; then
  echo "🌱 Creo ambiente virtuale in $VENV_DIR..."
  python3 -m venv $VENV_DIR
fi

source $VENV_DIR/bin/activate

echo "📦 Installo dipendenze..."
pip install -r requirements.txt

echo "📄 Carico variabili da .env..."
export $(grep -v '^#' .env | xargs)

echo "🚀 Avvio script di monitoraggio..."
python main.py

deactivate
