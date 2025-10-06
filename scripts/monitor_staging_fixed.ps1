# Sprint 1 Staging Metrics Monitor (Fixed)
# Monitors Circuit Breaker, Connection Pool, and Semantic Cache metrics
# Usage: .\scripts\monitor_staging_fixed.ps1

Write-Host "🚀 Sprint 1 Staging Metrics Monitor Started" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop monitoring`n" -ForegroundColor Yellow

$iteration = 0

while ($true) {
    $iteration++
    Clear-Host

    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "         🚀 SPRINT 1 STAGING METRICS - Iteration #$iteration" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor White
    Write-Host ""

    # 1. Circuit Breaker Metrics
    Write-Host "━━━ 1️⃣ CIRCUIT BREAKER ━━━" -ForegroundColor Green
    try {
        $cb = Invoke-RestMethod -Uri "http://localhost:8001/api/circuit-breaker/metrics" -TimeoutSec 5
        $cbClient = $cb.circuit_breakers.ollama_client

        Write-Host "  State: " -NoNewline -ForegroundColor White
        if ($cbClient.state -eq "closed") {
            Write-Host $cbClient.state.ToUpper() -ForegroundColor Green
        } elseif ($cbClient.state -eq "open") {
            Write-Host $cbClient.state.ToUpper() -ForegroundColor Red
        } else {
            Write-Host $cbClient.state.ToUpper() -ForegroundColor Yellow
        }

        Write-Host "  Total Calls: $($cbClient.total_calls)" -ForegroundColor White
        Write-Host "  Success Rate: $([math]::Round($cbClient.success_rate_percent, 2))%" -ForegroundColor White
        Write-Host "  Consecutive Successes: $($cbClient.consecutive_successes)" -ForegroundColor White
        Write-Host "  Consecutive Failures: $($cbClient.consecutive_failures)" -ForegroundColor White
        Write-Host "  State Transitions: $($cbClient.state_transitions)" -ForegroundColor White

        if ($cbClient.state -eq "closed") {
            Write-Host "  Status: ✅ HEALTHY" -ForegroundColor Green
        } else {
            Write-Host "  Status: ⚠️  NEEDS ATTENTION" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "  ❌ Circuit Breaker metrics unavailable" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Gray
    }

    Write-Host ""

    # 2. Connection Pool Metrics
    Write-Host "━━━ 2️⃣ CONNECTION POOL ━━━" -ForegroundColor Green
    try {
        $pool = Invoke-RestMethod -Uri "http://localhost:8001/api/connection-pool/metrics" -TimeoutSec 5

        Write-Host "  Total Requests: $($pool.connection_pool.total_requests)" -ForegroundColor White
        Write-Host "  Pool Connections: $($pool.connection_pool.pool_config.pool_connections)" -ForegroundColor White
        Write-Host "  Pool Max Size: $($pool.connection_pool.pool_config.pool_maxsize)" -ForegroundColor White
        Write-Host "  Pool Block: $($pool.connection_pool.pool_config.pool_block)" -ForegroundColor White
        Write-Host "  Status: ✅ ACTIVE" -ForegroundColor Green
    }
    catch {
        Write-Host "  ❌ Connection Pool metrics unavailable" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Gray
    }

    Write-Host ""

    # 3. Semantic Cache Metrics
    Write-Host "━━━ 3️⃣ SEMANTIC CACHE ━━━" -ForegroundColor Green
    try {
        $cache = Invoke-RestMethod -Uri "http://localhost:8001/api/semantic-cache/metrics" -TimeoutSec 5

        if ($cache.semantic_cache.enabled) {
            $hitRate = [math]::Round($cache.semantic_cache.hit_rate * 100, 2)
            $cacheSize = $cache.semantic_cache.cache_size
            $maxSize = $cache.semantic_cache.max_size
            $fillPercent = if ($maxSize -gt 0) { [math]::Round(($cacheSize / $maxSize) * 100, 2) } else { 0 }

            Write-Host "  Enabled: YES ✅" -ForegroundColor Green
            Write-Host "  Hit Rate: $hitRate% $(if ($hitRate -ge 30) {'✅'} elseif ($hitRate -ge 20) {'⚡'} else {'📊'})" -ForegroundColor White
            Write-Host "  Hits: $($cache.semantic_cache.hits)" -ForegroundColor White
            Write-Host "  Misses: $($cache.semantic_cache.misses)" -ForegroundColor White
            Write-Host "  Cache Size: $cacheSize / $maxSize ($fillPercent% full)" -ForegroundColor White
            Write-Host "  Similarity Threshold: $($cache.semantic_cache.similarity_threshold)" -ForegroundColor White

            if ($hitRate -ge 30) {
                Write-Host "  Status: ✅ EXCELLENT (Target: >30%)" -ForegroundColor Green
            } elseif ($hitRate -ge 20) {
                Write-Host "  Status: ⚡ GOOD (Target: >30%)" -ForegroundColor Yellow
            } else {
                Write-Host "  Status: 📊 WARMING UP (Target: >30%)" -ForegroundColor White
            }
        }
        else {
            Write-Host "  Enabled: NO ⚠️" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "  ❌ Semantic Cache metrics unavailable" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "Next update in 30 seconds... (Ctrl+C to stop)" -ForegroundColor Gray
    Write-Host ""

    Start-Sleep -Seconds 30
}
