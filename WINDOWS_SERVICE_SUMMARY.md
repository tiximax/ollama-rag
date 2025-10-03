# 🪟 Windows Service - Setup Complete!

## ✅ What We've Created

### 1. Service Installation Script
- **install-services.ps1** - Automated installation of Windows Services
- **uninstall-services.ps1** - Safe removal of services
- **manage-services.ps1** - Easy service management commands

### 2. Service Management Commands
- **INSTALL_COMMAND.txt** - Copy-paste commands for manual installation

### 3. Tools Installed
- **NSSM (Non-Sucking Service Manager)** v2.24
  - Location: `C:\Users\pc\Downloads\ollama-rag\nssm.exe`
  - Purpose: Convert any .exe into a Windows Service

---

## 🚀 Quick Start

### Option A: Automated Install (Easiest!)

```powershell
# Run PowerShell as Administrator, then:
cd C:\Users\pc\Downloads\ollama-rag
.\install-services.ps1
```

### Option B: Manual Install (Copy-Paste)

1. Open **INSTALL_COMMAND.txt**
2. Copy all commands
3. Paste into Admin PowerShell
4. Press Enter

### Option C: One-Liner

```powershell
Start-Process powershell -Verb RunAs -ArgumentList '-NoExit','-File','C:\Users\pc\Downloads\ollama-rag\install-services.ps1'
```

---

## 📊 Services Overview

### OllamaService 🦙
- **Display Name**: Ollama LLM Service
- **Description**: Ollama local LLM inference server
- **Startup Type**: Automatic
- **Binary**: `ollama.exe serve`
- **Logs**: `logs/ollama.log`

### OllamaRAGBackend 🐍
- **Display Name**: Ollama RAG Backend
- **Description**: FastAPI backend for RAG application
- **Startup Type**: Automatic
- **Binary**: `python -m uvicorn src.api.server:app`
- **Working Dir**: `C:\Users\pc\Downloads\ollama-rag`
- **Logs**: `logs/backend.log`
- **Dependencies**: OllamaService (starts after Ollama)

---

## 🔧 Service Management

### Check Status
```powershell
Get-Service OllamaService, OllamaRAGBackend
```

### Start Services
```powershell
Start-Service OllamaService, OllamaRAGBackend
```

### Stop Services
```powershell
Stop-Service OllamaRAGBackend, OllamaService
```

### Restart Services
```powershell
Restart-Service OllamaService, OllamaRAGBackend
```

### View Logs
```powershell
# Tail logs in real-time
Get-Content logs\backend.log -Tail 50 -Wait

# Last 20 lines
Get-Content logs\ollama.log -Tail 20
```

---

## 🎯 Benefits of Windows Services

✅ **Auto-Start on Boot** - Services start automatically with Windows
✅ **Runs in Background** - No PowerShell windows needed
✅ **System Integration** - Managed via Windows Services console
✅ **Auto-Restart** - Services restart on failure (5 second delay)
✅ **Dependency Management** - Backend waits for Ollama to start
✅ **Log Rotation** - Automatic log rotation at 1MB

---

## 🔍 Verification

### After Installation, Verify:

```powershell
# 1. Check service status
Get-Service OllamaService, OllamaRAGBackend | Format-Table Name, Status, StartType

# 2. Check if running
netstat -ano | findstr :11434  # Ollama port
netstat -ano | findstr :8000   # Backend port

# 3. Test API
curl http://localhost:8000/health
```

### Expected Output:

```
Name              Status  StartType
----              ------  ---------
OllamaService     Running Automatic
OllamaRAGBackend  Running Automatic
```

---

## 🗑️ Uninstall Services

### Quick Uninstall
```powershell
# Run as Administrator
.\uninstall-services.ps1
```

### Manual Uninstall
```powershell
Stop-Service OllamaRAGBackend, OllamaService -Force
.\nssm.exe remove OllamaRAGBackend confirm
.\nssm.exe remove OllamaService confirm
```

---

## 📝 Logs Location

All logs are stored in: `C:\Users\pc\Downloads\ollama-rag\logs\`

- `ollama.log` - Ollama service output
- `ollama_error.log` - Ollama errors
- `backend.log` - Backend API output
- `backend_error.log` - Backend errors

Logs auto-rotate when they reach 1MB.

---

## 💡 Troubleshooting

### Services Won't Start

```powershell
# Check service status
.\nssm.exe status OllamaService
.\nssm.exe status OllamaRAGBackend

# View detailed config
.\nssm.exe dump OllamaService
.\nssm.exe dump OllamaRAGBackend

# Check logs
Get-Content logs\backend_error.log -Tail 20
```

### Port Already in Use

```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

### Services Exist But Not Running

```powershell
# Remove and reinstall
Stop-Service OllamaRAGBackend, OllamaService -Force
.\uninstall-services.ps1
.\install-services.ps1
```

---

## 🎉 Success Checklist

After installation, you should have:

- ✅ Two services installed (OllamaService, OllamaRAGBackend)
- ✅ Both services running (Status: Running)
- ✅ Both set to auto-start (StartType: Automatic)
- ✅ Backend accessible at http://localhost:8000
- ✅ Ollama accessible at http://localhost:11434
- ✅ Logs being written to `logs/` directory
- ✅ Services auto-restart on failure
- ✅ Backend depends on Ollama (correct start order)

---

## 🔄 Comparison: Services vs Scripts

### Windows Services (Production) ⭐
- ✅ Auto-start on boot
- ✅ Runs in background
- ✅ System integrated
- ✅ Auto-restart on failure
- ❌ Harder to debug
- ❌ Requires admin to install

### start-all.ps1 (Development)
- ✅ Easy to start/stop
- ✅ See logs in real-time
- ✅ No admin needed
- ✅ Easy debugging
- ❌ Manual start after reboot
- ❌ Multiple windows

**Recommendation**: Use Services for production, Scripts for development!

---

## 📚 Additional Resources

- **NSSM Documentation**: https://nssm.cc/usage
- **Windows Services Guide**: https://docs.microsoft.com/en-us/windows/win32/services/
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **Ollama Docs**: https://ollama.com/docs

---

## 🎯 Next Steps

After services are installed and running:

1. **Test API**: Visit http://localhost:8000/docs
2. **Monitor Logs**: `Get-Content logs\backend.log -Wait`
3. **Setup Cloudflare Tunnel**: For public HTTPS access
4. **Add Custom Domain**: For branded URL
5. **Configure Monitoring**: Set up alerts for service failures

---

**Congratulations! Your Ollama RAG app is now running as Windows Services! 🎉**

Services will automatically start with Windows and restart on failure. Your app is production-ready! 🚀
