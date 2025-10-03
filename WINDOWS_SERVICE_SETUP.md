# 🪟 Windows Service Setup Guide

Setup Cloudflare Tunnel và Backend như Windows Services để tự động khởi động cùng Windows!

## 📋 Prerequisites

- PowerShell với Admin privileges
- NSSM (Non-Sucking Service Manager) - optional nhưng recommended

---

## Option 1: Setup với Cloudflared Built-in Service (Recommended) ⭐

### 1. Install Cloudflared as Service

```powershell
# Run as Administrator
cd C:\Users\pc\Downloads\ollama-rag

# Install cloudflared service
.\cloudflared.exe service install
```

### 2. Configure Service

Cloudflared sẽ tự động sử dụng file config. Tạo file `config.yml` trong `C:\Users\pc\.cloudflared\`:

```powershell
# Copy config to cloudflared config directory
Copy-Item .\cloudflare-tunnel-config.yml C:\Users\pc\.cloudflared\config.yml
```

### 3. Start Service

```powershell
# Start service
.\cloudflared.exe service start

# Check status
Get-Service cloudflared

# View logs
Get-EventLog -LogName Application -Source cloudflared -Newest 10
```

### 4. Uninstall Service (if needed)

```powershell
.\cloudflared.exe service uninstall
```

---

## Option 2: Setup với NSSM (More Control) 🎛️

### 1. Download NSSM

```powershell
# Download NSSM
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "$env:TEMP\nssm.zip"

# Extract
Expand-Archive -Path "$env:TEMP\nssm.zip" -DestinationPath "$env:TEMP\nssm"

# Copy to project
Copy-Item "$env:TEMP\nssm\nssm-2.24\win64\nssm.exe" C:\Users\pc\Downloads\ollama-rag\
```

### 2. Install Backend as Service

```powershell
# Run as Administrator
cd C:\Users\pc\Downloads\ollama-rag

# Install backend service
.\nssm.exe install OllamaRAGBackend "C:\Windows\System32\cmd.exe" "/c cd C:\Users\pc\Downloads\ollama-rag && uvicorn src.api.server:app --host 0.0.0.0 --port 8000"

# Configure service
.\nssm.exe set OllamaRAGBackend DisplayName "Ollama RAG Backend API"
.\nssm.exe set OllamaRAGBackend Description "FastAPI backend for Ollama RAG application"
.\nssm.exe set OllamaRAGBackend Start SERVICE_AUTO_START

# Start service
.\nssm.exe start OllamaRAGBackend
```

### 3. Install Cloudflare Tunnel as Service

```powershell
# Install tunnel service
.\nssm.exe install OllamaRAGTunnel "C:\Users\pc\Downloads\ollama-rag\cloudflared.exe" "tunnel --url http://localhost:8000"

# Configure service
.\nssm.exe set OllamaRAGTunnel DisplayName "Ollama RAG Cloudflare Tunnel"
.\nssm.exe set OllamaRAGTunnel Description "Cloudflare Tunnel for public HTTPS access"
.\nssm.exe set OllamaRAGTunnel Start SERVICE_AUTO_START
.\nssm.exe set OllamaRAGTunnel AppStdout "C:\Users\pc\Downloads\ollama-rag\logs\tunnel.log"
.\nssm.exe set OllamaRAGTunnel AppStderr "C:\Users\pc\Downloads\ollama-rag\logs\tunnel_error.log"

# Start service
.\nssm.exe start OllamaRAGTunnel
```

### 4. Manage Services

```powershell
# Check status
Get-Service OllamaRAGBackend
Get-Service OllamaRAGTunnel

# Start services
Start-Service OllamaRAGBackend
Start-Service OllamaRAGTunnel

# Stop services
Stop-Service OllamaRAGBackend
Stop-Service OllamaRAGTunnel

# Remove services
.\nssm.exe remove OllamaRAGBackend confirm
.\nssm.exe remove OllamaRAGTunnel confirm
```

---

## Option 3: Setup Ollama as Service 🦙

Ollama có thể chạy như service nếu cài từ installer. Nếu chưa, setup manually:

```powershell
# Install Ollama as service with NSSM
.\nssm.exe install OllamaService "C:\Users\pc\AppData\Local\Programs\Ollama\ollama.exe" "serve"

# Configure
.\nssm.exe set OllamaService DisplayName "Ollama LLM Service"
.\nssm.exe set OllamaService Description "Ollama local LLM inference server"
.\nssm.exe set OllamaService Start SERVICE_AUTO_START

# Start service
.\nssm.exe start OllamaService
```

---

## 🎯 Complete Auto-Start Setup

Để tất cả services tự động start cùng Windows:

```powershell
# 1. Install all services (run as Admin)
.\nssm.exe install OllamaService "ollama" "serve"
.\nssm.exe install OllamaRAGBackend "python" "-m uvicorn src.api.server:app --host 0.0.0.0 --port 8000"
.\cloudflared.exe service install

# 2. Configure dependencies (Backend depends on Ollama)
.\nssm.exe set OllamaRAGBackend DependOnService OllamaService

# 3. Set all to auto-start
.\nssm.exe set OllamaService Start SERVICE_AUTO_START
.\nssm.exe set OllamaRAGBackend Start SERVICE_AUTO_START

# 4. Start all
.\nssm.exe start OllamaService
.\nssm.exe start OllamaRAGBackend
.\cloudflared.exe service start
```

---

## 📊 Verify Services

```powershell
# Check all services
Get-Service | Where-Object {$_.Name -like "*Ollama*" -or $_.Name -like "*cloudflared*"}

# Check if running
Test-NetConnection localhost -Port 11434  # Ollama
Test-NetConnection localhost -Port 8000   # Backend

# View Windows Event Logs
Get-EventLog -LogName Application -Source OllamaRAGBackend -Newest 10
```

---

## 🔧 Troubleshooting

### Service won't start

```powershell
# Check service status
.\nssm.exe status OllamaRAGBackend

# View detailed info
.\nssm.exe dump OllamaRAGBackend

# Check logs
Get-Content C:\Users\pc\Downloads\ollama-rag\logs\tunnel.log -Tail 50
```

### Permission issues

```powershell
# Run PowerShell as Administrator
Start-Process powershell -Verb RunAs
```

### Port conflicts

```powershell
# Check what's using ports
netstat -ano | findstr :8000
netstat -ano | findstr :11434

# Kill process if needed
taskkill /PID <PID> /F
```

---

## 💡 Best Practices

1. **Always run service installs as Administrator**
2. **Set proper working directories** for services
3. **Configure logging** to track issues
4. **Set dependencies** (Backend depends on Ollama)
5. **Use auto-restart** on failure

```powershell
# Enable auto-restart on failure
.\nssm.exe set OllamaRAGBackend AppExit Default Restart
.\nssm.exe set OllamaRAGBackend AppRestartDelay 5000  # 5 seconds
```

---

## 🎉 Quick Commands Cheat Sheet

```powershell
# Start all services
Start-Service OllamaService, OllamaRAGBackend; .\cloudflared.exe service start

# Stop all services
Stop-Service OllamaService, OllamaRAGBackend; .\cloudflared.exe service stop

# Restart all
Restart-Service OllamaService, OllamaRAGBackend; .\cloudflared.exe service stop; .\cloudflared.exe service start

# Check status
Get-Service OllamaService, OllamaRAGBackend, cloudflared
```

---

**Note:** Cloudflare Quick Tunnel không thể chạy như service vì nó generate random URL mỗi lần. Để có URL cố định, cần setup **Named Tunnel** với domain riêng (xem `CLOUDFLARE_TUNNEL_SETUP.md`).
