# Auto-merge PR when CI passes
# Usage: .\scripts\auto_merge_pr.ps1 -PRNumber 30

param(
    [Parameter(Mandatory=$true)]
    [int]$PRNumber,

    [int]$MaxWaitMinutes = 10,
    [int]$CheckIntervalSeconds = 15
)

Write-Host "🤖 Auto-merge script started for PR #$PRNumber" -ForegroundColor Cyan
Write-Host "Will check every $CheckIntervalSeconds seconds for up to $MaxWaitMinutes minutes" -ForegroundColor Gray
Write-Host ""

$startTime = Get-Date
$maxWaitTime = $startTime.AddMinutes($MaxWaitMinutes)

while ((Get-Date) -lt $maxWaitTime) {
    $elapsed = (Get-Date) - $startTime
    Write-Host "⏱️  Elapsed: $($elapsed.Minutes)m $($elapsed.Seconds)s - Checking CI status..." -ForegroundColor Yellow

    # Check CI status
    $checks = gh pr checks $PRNumber --json state,conclusion 2>&1

    if ($LASTEXITCODE -eq 0) {
        $checksData = $checks | ConvertFrom-Json

        # Count check states
        $pending = ($checksData | Where-Object { $_.state -eq "PENDING" }).Count
        $success = ($checksData | Where-Object { $_.conclusion -eq "SUCCESS" }).Count
        $failure = ($checksData | Where-Object { $_.conclusion -eq "FAILURE" }).Count
        $total = $checksData.Count

        Write-Host "   📊 Status: $success/$total passed, $pending pending, $failure failed" -ForegroundColor Gray

        # If all checks passed
        if ($pending -eq 0 -and $failure -eq 0 -and $success -eq $total) {
            Write-Host ""
            Write-Host "✅ All CI checks passed!" -ForegroundColor Green
            Write-Host "🚀 Merging PR #$PRNumber..." -ForegroundColor Cyan

            # Merge PR
            gh pr merge $PRNumber --squash --delete-branch

            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Host "🎉 PR #$PRNumber merged successfully!" -ForegroundColor Green
                Write-Host "✨ Branch deleted" -ForegroundColor Gray

                # Return to master
                git checkout master
                git pull origin master

                Write-Host ""
                Write-Host "📍 Switched to master and pulled latest changes" -ForegroundColor Cyan
                Write-Host ""
                Write-Host "🎯 Issue #27 should be automatically closed!" -ForegroundColor Green

                exit 0
            } else {
                Write-Host ""
                Write-Host "❌ Failed to merge PR" -ForegroundColor Red
                exit 1
            }
        }

        # If any checks failed
        if ($failure -gt 0) {
            Write-Host ""
            Write-Host "❌ Some CI checks failed!" -ForegroundColor Red
            Write-Host "Please review the failures and fix them." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "View PR: https://github.com/tiximax/ollama-rag/pull/$PRNumber" -ForegroundColor Cyan
            exit 1
        }

        # Still pending, wait and retry
        if ($pending -gt 0) {
            Write-Host "   ⏳ Waiting $CheckIntervalSeconds seconds..." -ForegroundColor Gray
            Start-Sleep -Seconds $CheckIntervalSeconds
        }
    } else {
        Write-Host "⚠️  Failed to check PR status, retrying..." -ForegroundColor Yellow
        Start-Sleep -Seconds $CheckIntervalSeconds
    }
}

Write-Host ""
Write-Host "⏰ Timeout: CI checks didn't complete within $MaxWaitMinutes minutes" -ForegroundColor Yellow
Write-Host "You can manually check and merge at:" -ForegroundColor Gray
Write-Host "https://github.com/tiximax/ollama-rag/pull/$PRNumber" -ForegroundColor Cyan
exit 1
