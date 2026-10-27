#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo 'Instala Python 3.11 o 3.12'; exit 1; }
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m compileall -q app.py src tests
pytest -q
echo 'Pruebas locales aprobadas. Esto no prueba credenciales ni servicios externos.'
