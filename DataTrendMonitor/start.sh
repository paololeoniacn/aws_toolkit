#!/bin/bash

# Crea virtualenv
python3 -m venv venv

# Attiva virtualenv
source venv/bin/activate

# Installa dipendenze (anche se è vuoto per ora)
pip install -r requirements.txt

# Esegui lo script
python main.py
