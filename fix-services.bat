@echo off
REM Fix Windows Service Paths
REM Run as Administrator!

echo ========================================
echo Fixing Ollama RAG Service Paths
echo ========================================
echo.

REM Check for admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Must run as Administrator!
    echo Right-click and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

cd /d "%~dp0"

echo Fixing Ollama Service path...
nssm.exe set OllamaService Application "C:\Users\pc\AppData\Local\Programs\Ollama\ollama.exe"
nssm.exe set OllamaService AppParameters "serve"
echo Done!
echo.

echo Fixing Backend Service path...
nssm.exe set OllamaRAGBackend Application "C:\Users\pc\AppData\Local\Programs\Python\Python312\python.exe"
nssm.exe set OllamaRAGBackend AppParameters "-m uvicorn src.api.server:app --host 0.0.0.0 --port 8000"
echo Done!
echo.

echo Starting Ollama Service...
net start OllamaService
timeout /t 3 /nobreak >nul

echo Starting Backend Service...
net start OllamaRAGBackend
echo.

echo ========================================
echo SUCCESS! Services fixed and started!
echo ========================================
echo.

sc query OllamaService
echo.
sc query OllamaRAGBackend
echo.

pause
