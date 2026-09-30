@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo Creando entorno virtual e instalando dependencias, espere...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
)

start "Backend - NO CERRAR" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
timeout /t 5 >nul
start "Frontend - NO CERRAR" cmd /k ".venv\Scripts\activate.bat && python frontend\main.py"
timeout /t 6 >nul
start http://localhost:8080
