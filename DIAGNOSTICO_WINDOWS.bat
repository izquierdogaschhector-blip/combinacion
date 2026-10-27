@echo off
cd /d %~dp0
echo === Diagnostico Combinacion Maestra V6 ===
where python
if errorlevel 1 (
  echo No se encuentra Python. Instala Python 3.11 o 3.12 y marca Add Python to PATH.
  pause
  exit /b 1
)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m compileall -q app.py src tests
pytest -q
if errorlevel 1 (
  echo Alguna comprobacion ha fallado. Copia el mensaje de error para diagnosticarlo.
  pause
  exit /b 1
)
echo Diagnostico terminado: pruebas locales aprobadas. Esto no prueba credenciales ni servicios externos.
pause
