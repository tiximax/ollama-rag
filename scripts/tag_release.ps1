param(
  [Parameter(Mandatory=$true)][string]$Version
)

# Validate version pattern vX.Y.Z
if ($Version -notmatch '^v\d+\.\d+\.\d+$') {
  Write-Error "Version must match vX.Y.Z (e.g., v0.1.0)"; exit 1
}

# Optional: ensure git status clean (skip strict enforcement)
try {
  git tag $Version
  git push origin $Version
  Write-Host "Tagged and pushed $Version" -ForegroundColor Green
} catch {
  Write-Error "Failed to tag/push: $($_.Exception.Message)"; exit 1
}
