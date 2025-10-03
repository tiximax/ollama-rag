# Semantic Cache Benchmark Script
# Measures latency and cache hit-rate for exact and similar queries

param(
  [string]$BaseQuery = "What is machine learning and how does it work?",
  [string]$SimilarQuery = "Explain machine learning and its working mechanisms",
  [int]$K = 3,
  [int]$ExactRepeats = 5,
  [int]$SimilarRepeats = 5
)

function Invoke-Query([string]$q, [int]$k) {
  $body = @{ query = $q; k = $k } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:8000/api/query" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 60
}

function Time-Query([string]$q, [int]$k) {
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $resp = Invoke-Query $q $k
  $sw.Stop()
  [pscustomobject]@{ ms = [math]::Round($sw.Elapsed.TotalMilliseconds,2); hit = [bool]$resp.cache_hit }
}

Write-Host "\n=== Semantic Cache Benchmark ===" -ForegroundColor Cyan
Write-Host ("Base Query   : {0}" -f $BaseQuery) -ForegroundColor White
Write-Host ("Similar Query: {0}" -f $SimilarQuery) -ForegroundColor White
$stats0 = Invoke-RestMethod -Uri "http://localhost:8000/api/cache-stats" -Method Get
if ($stats0.semantic_cache) {
  Write-Host ("Threshold={0} TTL={1}s Size={2} Hits={3} Misses={4}" -f $stats0.semantic_cache.similarity_threshold,$stats0.semantic_cache.ttl,$stats0.semantic_cache.size,$stats0.semantic_cache.hits,$stats0.semantic_cache.misses) -ForegroundColor Yellow
}

# Seed MISS to populate cache
Write-Host "\nSeeding with base query (MISS expected on first run)..." -ForegroundColor Yellow
$seed = Time-Query $BaseQuery $K
Write-Host ("  Seed: {0} ms, hit={1}" -f $seed.ms,$seed.hit) -ForegroundColor White

# EXACT repeats (HIT expected)
$exactTimes = @()
for ($i=1; $i -le $ExactRepeats; $i++) {
  $r = Time-Query $BaseQuery $K
  $exactTimes += $r.ms
  Write-Host ("  Exact[{0}]: {1} ms, hit={2}" -f $i,$r.ms,$r.hit) -ForegroundColor Green
}

# SIMILAR repeats (semantic HIT expected depending on threshold)
$similarTimes = @()
for ($i=1; $i -le $SimilarRepeats; $i++) {
  $r = Time-Query $SimilarQuery $K
  $similarTimes += $r.ms
  Write-Host ("  Similar[{0}]: {1} ms, hit={2}" -f $i,$r.ms,$r.hit) -ForegroundColor Green
}

function Avg($arr) { if ($arr.Count -eq 0) { return 0 } else { return [math]::Round(($arr | Measure-Object -Average).Average,2) } }
$avgExact = Avg $exactTimes
$avgSimilar = Avg $similarTimes

Write-Host "\nResults:" -ForegroundColor Magenta
Write-Host ("  Seed (MISS): {0} ms" -f $seed.ms) -ForegroundColor Yellow
Write-Host ("  Avg EXACT (HIT): {0} ms" -f $avgExact) -ForegroundColor Green
Write-Host ("  Avg SIMILAR (HIT): {0} ms" -f $avgSimilar) -ForegroundColor Green
if ($avgExact -gt 0) { $speedup = [math]::Round($seed.ms / $avgExact, 2); Write-Host ("  Speedup EXACT: {0}x" -f $speedup) -ForegroundColor Cyan }
if ($avgSimilar -gt 0) { $speedup2 = [math]::Round($seed.ms / $avgSimilar, 2); Write-Host ("  Speedup SIMILAR: {0}x" -f $speedup2) -ForegroundColor Cyan }

$stats = Invoke-RestMethod -Uri "http://localhost:8000/api/cache-stats" -Method Get
if ($stats.semantic_cache) {
  Write-Host ("\nCache Stats: size={0} hits={1} misses={2} hit_rate={3:P0} semantic_hits={4}" -f $stats.semantic_cache.size,$stats.semantic_cache.hits,$stats.semantic_cache.misses,$stats.semantic_cache.hit_rate,$stats.semantic_cache.semantic_hits) -ForegroundColor White
}
