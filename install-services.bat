@echo off
REM Windows Service Installation Batch File
REM This will request admin privileges automatically

echo ========================================
echo Installing Ollama RAG Windows Services
echo ========================================
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with Administrator privileges...
    echo.
    
    cd /d "%~dp0"
    
    REM Install Ollama Service
    echo [1/2] Installing Ollama Service...
    nssm.exe install OllamaService ollama serve
    nssm.exe set OllamaService DisplayName "Ollama LLM Service"
    nssm.exe set OllamaService Start SERVICE_AUTO_START
    nssm.exe set OllamaService AppStdout "%~dp0logs\ollama.log"
    nssm.exe set OllamaService AppStderr "%~dp0logs\ollama_error.log"
    echo Done!
    echo.
    
    REM Install Backend Service
    echo [2/2] Installing Backend Service...
    nssm.exe install OllamaRAGBackend python "-m uvicorn src.api.server:app --host 0.0.0.0 --port 8000"
    nssm.exe set OllamaRAGBackend DisplayName "Ollama RAG Backend"
    nssm.exe set OllamaRAGBackend Start SERVICE_AUTO_START
    nssm.exe set OllamaRAGBackend AppDirectory "%~dp0"
    nssm.exe set OllamaRAGBackend AppStdout "%~dp0logs\backend.log"
    nssm.exe set OllamaRAGBackend AppStderr "%~dp0logs\backend_error.log"
    nssm.exe set OllamaRAGBackend DependOnService OllamaService
    echo Done!
    echo.
    
    REM Start Services
    echo Starting services...
    net start OllamaService
    timeout /t 3 /nobreak >nul
    net start OllamaRAGBackend
    echo.
    
    echo ========================================
    echo SUCCESS! Services installed and started
    echo ========================================
    echo.
    echo Services will auto-start on Windows boot!
    echo.
    echo Check status: sc query OllamaService
    echo               sc query OllamaRAGBackend
    echo.
    pause
) else (
    echo ERROR: Administrator privileges required!
    echo.
    echo Right-click this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)
