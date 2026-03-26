@echo off
TITLE Meridian Engine Controller
echo ==========================================================
echo Starting Meridian Autonomous Research Engine...
echo ==========================================================

echo [1/4] Terminating existing background processes on ports 8000 and 5173...
FOR /F "tokens=5" %%a IN ('netstat -aon ^| findstr :8000') DO taskkill /F /PID %%a 2>nul
FOR /F "tokens=5" %%a IN ('netstat -aon ^| findstr :5173') DO taskkill /F /PID %%a 2>nul
taskkill /F /IM celery.exe 2>nul
echo Cleaning up done.

echo [2/4] Booting Celery Background Worker...
start "Meridian Celery Worker" cmd /k ".\venv\Scripts\activate.bat && set PYTHONPATH=%cd% && celery -A src.meridian.interfaces.workers.app worker --loglevel=info -P solo"

echo [3/4] Booting FastAPI Backend...
start "Meridian FastAPI API" cmd /k ".\venv\Scripts\activate.bat && set PYTHONPATH=%cd% && uvicorn src.meridian.interfaces.api.main:app --reload --port 8000"

echo [4/4] Booting React/Vite Frontend Dashboard...
start "Meridian UI Dashboard" cmd /k "cd frontend && npm run dev"

echo.
echo ==========================================================
echo All services have been dispatched. 
echo Allow ~5 seconds for the backend and Vite to compile.
echo Application will be available at: http://localhost:5173
echo.
echo To close Meridian completely, exit the 3 command prompt windows.
echo ==========================================================
pause
