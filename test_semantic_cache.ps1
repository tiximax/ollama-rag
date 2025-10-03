# Test Semantic Cache Functionality
# This script tests if semantic caching is working correctly

Write-Host "`n🧪 Testing Semantic Cache Functionality..." -ForegroundColor Cyan
Write-Host "=" * 60

# Test 1: First query (should be MISS)
Write-Host "`n📝 Test 1: First query (Cache MISS expected)..." -ForegroundColor Yellow
$body1 = @{
    query = "What is RAG?"
    k = 3
} | ConvertTo-Json

$start1 = Get-Date
$response1 = Invoke-RestMethod -Uri "http://localhost:8000/api/query" -Method Post -Body $body1 -ContentType "application/json"
$end1 = Get-Date
$time1 = ($end1 - $start1).TotalMilliseconds

Write-Host "✅ Response received in $([math]::Round($time1, 2))ms" -ForegroundColor Green
Write-Host "Cache Hit: $($response1.cache_hit)" -ForegroundColor $(if ($response1.cache_hit) { "Green" } else { "Yellow" })
Write-Host "Answer preview: $($response1.answer.Substring(0, [Math]::Min(100, $response1.answer.Length)))..."

# Wait a bit
Start-Sleep -Seconds 2

# Test 2: Same query (should be HIT)
Write-Host "`n📝 Test 2: Same query (Cache HIT expected)..." -ForegroundColor Yellow
$start2 = Get-Date
$response2 = Invoke-RestMethod -Uri "http://localhost:8000/api/query" -Method Post -Body $body1 -ContentType "application/json"
$end2 = Get-Date
$time2 = ($end2 - $start2).TotalMilliseconds

Write-Host "✅ Response received in $([math]::Round($time2, 2))ms" -ForegroundColor Green
Write-Host "Cache Hit: $($response2.cache_hit)" -ForegroundColor $(if ($response2.cache_hit) { "Green" } else { "Red" })
Write-Host "Speedup: $([math]::Round($time1 / $time2, 2))x faster!" -ForegroundColor Cyan

if ($response2.cache_metadata) {
    Write-Host "`nCache Metadata:" -ForegroundColor Cyan
    Write-Host "  - Type: $($response2.cache_metadata.cache_type)"
    Write-Host "  - Similarity: $($response2.cache_metadata.similarity)"
    Write-Host "  - Original Query: $($response2.cache_metadata.original_query)"
}

# Wait a bit
Start-Sleep -Seconds 2

# Test 3: Similar query (should be semantic HIT)
Write-Host "`n📝 Test 3: Similar query (Semantic HIT expected)..." -ForegroundColor Yellow
$body3 = @{
    query = "Can you explain what RAG is?"
    k = 3
} | ConvertTo-Json

$start3 = Get-Date
$response3 = Invoke-RestMethod -Uri "http://localhost:8000/api/query" -Method Post -Body $body3 -ContentType "application/json"
$end3 = Get-Date
$time3 = ($end3 - $start3).TotalMilliseconds

Write-Host "✅ Response received in $([math]::Round($time3, 2))ms" -ForegroundColor Green
Write-Host "Cache Hit: $($response3.cache_hit)" -ForegroundColor $(if ($response3.cache_hit) { "Green" } else { "Yellow" })

if ($response3.cache_metadata) {
    Write-Host "`nCache Metadata:" -ForegroundColor Cyan
    Write-Host "  - Type: $($response3.cache_metadata.cache_type)"
    Write-Host "  - Similarity: $([math]::Round($response3.cache_metadata.similarity, 4))"
    Write-Host "  - Original Query: $($response3.cache_metadata.original_query)"
}

# Check cache stats
Write-Host "`n📊 Cache Statistics:" -ForegroundColor Cyan
Write-Host "=" * 60
$stats = Invoke-RestMethod -Uri "http://localhost:8000/api/cache-stats"

if ($stats.semantic_cache) {
    Write-Host "Semantic Cache:" -ForegroundColor Green
    Write-Host "  - Hits: $($stats.semantic_cache.hits)"
    Write-Host "  - Misses: $($stats.semantic_cache.misses)"
    Write-Host "  - Hit Rate: $([math]::Round($stats.semantic_cache.hit_rate * 100, 2))%"
    Write-Host "  - Exact Hits: $($stats.semantic_cache.exact_hits)"
    Write-Host "  - Semantic Hits: $($stats.semantic_cache.semantic_hits)"
    Write-Host "  - Cache Size: $($stats.semantic_cache.size)/$($stats.semantic_cache.max_size)"
} else {
    Write-Host "⚠️  Semantic cache stats not available" -ForegroundColor Yellow
}

Write-Host "`n✅ Test completed!" -ForegroundColor Green
Write-Host "=" * 60
