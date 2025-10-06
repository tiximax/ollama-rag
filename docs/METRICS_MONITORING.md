# 📊 Metrics Monitoring Guide

**Status**: ✅ Production Ready
**Version**: 1.0
**Sprint**: Sprint 2 - Metrics Dashboard

---

## 🎯 Overview

Ollama RAG provides comprehensive Prometheus metrics to monitor system health, performance, and reliability. This guide covers setup, available metrics, and best practices.

---

## 🔧 Quick Start

### 1. Access Metrics Endpoint

```bash
# Prometheus format metrics
curl http://localhost:8000/metrics

# Human-readable cache stats
curl http://localhost:8000/api/cache-stats
```

### 2. Setup Prometheus (Optional)

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ollama-rag'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
```

### 3. Run Prometheus

```bash
prometheus --config.file=prometheus.yml
```

---

## 📊 Available Metrics

### Circuit Breaker Metrics

Monitor circuit breaker health and state transitions.

#### `ollama_rag_circuit_breaker_state`
**Type**: Gauge
**Labels**: `breaker_name`
**Values**: 0=CLOSED, 1=OPEN, 2=HALF_OPEN

**Example**:
```
ollama_rag_circuit_breaker_state{breaker_name="ollama_client"} 0.0
```

**Use Case**: Alert when circuit opens (value=1)

#### `ollama_rag_circuit_breaker_calls_total`
**Type**: Counter
**Labels**: `breaker_name`, `status`
**Status values**: success, failure, rejected

**Example**:
```
ollama_rag_circuit_breaker_calls_total{breaker_name="ollama_client",status="success"} 150.0
ollama_rag_circuit_breaker_calls_total{breaker_name="ollama_client",status="failure"} 5.0
ollama_rag_circuit_breaker_calls_total{breaker_name="ollama_client",status="rejected"} 2.0
```

**Queries**:
```promql
# Success rate
rate(ollama_rag_circuit_breaker_calls_total{status="success"}[5m])
/
rate(ollama_rag_circuit_breaker_calls_total[5m])

# Failure rate
rate(ollama_rag_circuit_breaker_calls_total{status="failure"}[5m])
```

#### `ollama_rag_circuit_breaker_transitions_total`
**Type**: Counter
**Labels**: `breaker_name`, `from_state`, `to_state`

**Example**:
```
ollama_rag_circuit_breaker_transitions_total{breaker_name="ollama_client",from_state="closed",to_state="open"} 3.0
```

**Use Case**: Track how often circuit opens/closes

#### `ollama_rag_circuit_breaker_consecutive_failures`
**Type**: Gauge
**Labels**: `breaker_name`

**Example**:
```
ollama_rag_circuit_breaker_consecutive_failures{breaker_name="ollama_client"} 2.0
```

**Alert Example**:
```yaml
- alert: HighConsecutiveFailures
  expr: ollama_rag_circuit_breaker_consecutive_failures > 3
  for: 1m
  annotations:
    summary: "High consecutive failures detected"
```

#### `ollama_rag_circuit_breaker_last_state_change_timestamp`
**Type**: Gauge (Unix timestamp)
**Labels**: `breaker_name`

**Query**:
```promql
# Time since last state change
time() - ollama_rag_circuit_breaker_last_state_change_timestamp
```

---

### Connection Pool Metrics

Monitor HTTP connection pool utilization and efficiency.

#### `ollama_rag_connection_pool_requests_total`
**Type**: Counter
**Labels**: `client_name`

**Example**:
```
ollama_rag_connection_pool_requests_total{client_name="ollama_client"} 1250.0
```

**Queries**:
```promql
# Request rate
rate(ollama_rag_connection_pool_requests_total[5m])

# Requests per minute
increase(ollama_rag_connection_pool_requests_total[1m])
```

#### `ollama_rag_connection_pool_size`
**Type**: Gauge
**Labels**: `client_name`, `pool_type`
**Pool types**: connections, maxsize

**Example**:
```
ollama_rag_connection_pool_size{client_name="ollama_client",pool_type="connections"} 10.0
ollama_rag_connection_pool_size{client_name="ollama_client",pool_type="maxsize"} 20.0
```

**Use Case**: Verify pool configuration is correct

---

### Semantic Cache Metrics

Monitor cache hit rates and efficiency.

#### `ollama_rag_semcache_hits_total`
**Type**: Counter
**Labels**: `type`
**Types**: exact, semantic

**Example**:
```
ollama_rag_semcache_hits_total{type="exact"} 85.0
ollama_rag_semcache_hits_total{type="semantic"} 42.0
```

**Queries**:
```promql
# Total cache hit rate
(
  rate(ollama_rag_semcache_hits_total[5m])
) / (
  rate(ollama_rag_semcache_hits_total[5m])
  + rate(ollama_rag_semcache_misses_total[5m])
)

# Semantic hit percentage
rate(ollama_rag_semcache_hits_total{type="semantic"}[5m])
/ rate(ollama_rag_semcache_hits_total[5m])
```

#### `ollama_rag_semcache_misses_total`
**Type**: Counter

**Example**:
```
ollama_rag_semcache_misses_total 18.0
```

#### `ollama_rag_semcache_size`
**Type**: Gauge

**Example**:
```
ollama_rag_semcache_size 245.0
```

#### `ollama_rag_semcache_fill_ratio`
**Type**: Gauge (0.0 to 1.0)

**Example**:
```
ollama_rag_semcache_fill_ratio 0.245
```

**Alert Example**:
```yaml
- alert: CacheAlmostFull
  expr: ollama_rag_semcache_fill_ratio > 0.9
  for: 5m
  annotations:
    summary: "Semantic cache is 90% full"
```

---

## 🎨 Grafana Dashboard (Optional)

### Basic Dashboard JSON

Save this as `grafana-dashboard.json`:

```json
{
  "dashboard": {
    "title": "Ollama RAG Metrics",
    "panels": [
      {
        "title": "Circuit Breaker State",
        "targets": [{
          "expr": "ollama_rag_circuit_breaker_state"
        }],
        "type": "stat"
      },
      {
        "title": "Request Success Rate",
        "targets": [{
          "expr": "rate(ollama_rag_circuit_breaker_calls_total{status=\"success\"}[5m]) / rate(ollama_rag_circuit_breaker_calls_total[5m])"
        }],
        "type": "graph"
      },
      {
        "title": "Cache Hit Rate",
        "targets": [{
          "expr": "rate(ollama_rag_semcache_hits_total[5m]) / (rate(ollama_rag_semcache_hits_total[5m]) + rate(ollama_rag_semcache_misses_total[5m]))"
        }],
        "type": "graph"
      },
      {
        "title": "Connection Pool Requests/sec",
        "targets": [{
          "expr": "rate(ollama_rag_connection_pool_requests_total[5m])"
        }],
        "type": "graph"
      }
    ]
  }
}
```

### Import to Grafana

1. Open Grafana UI
2. Create → Import
3. Paste JSON or upload file
4. Select Prometheus data source
5. Save dashboard

---

## 🚨 Recommended Alerts

### Critical Alerts

```yaml
groups:
  - name: ollama_rag_critical
    rules:
      # Circuit breaker opened
      - alert: CircuitBreakerOpen
        expr: ollama_rag_circuit_breaker_state == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker {{ $labels.breaker_name }} is OPEN"
          description: "Service {{ $labels.breaker_name }} is experiencing issues"

      # High failure rate
      - alert: HighFailureRate
        expr: |
          rate(ollama_rag_circuit_breaker_calls_total{status="failure"}[5m])
          / rate(ollama_rag_circuit_breaker_calls_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High failure rate detected"
          description: "Failure rate is {{ $value | humanizePercentage }}"
```

### Warning Alerts

```yaml
      # Low cache hit rate
      - alert: LowCacheHitRate
        expr: |
          rate(ollama_rag_semcache_hits_total[5m])
          / (rate(ollama_rag_semcache_hits_total[5m]) + rate(ollama_rag_semcache_misses_total[5m]))
          < 0.3
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate is low"
          description: "Hit rate is {{ $value | humanizePercentage }}"

      # Cache almost full
      - alert: CacheAlmostFull
        expr: ollama_rag_semcache_fill_ratio > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Semantic cache is almost full"
```

---

## 📈 Useful Queries

### Performance Queries

```promql
# Average requests per second (last 5 min)
rate(ollama_rag_connection_pool_requests_total[5m])

# Total requests in last hour
increase(ollama_rag_connection_pool_requests_total[1h])

# Success rate percentage
100 * rate(ollama_rag_circuit_breaker_calls_total{status="success"}[5m])
/ rate(ollama_rag_circuit_breaker_calls_total[5m])

# Cache effectiveness (hits vs total)
rate(ollama_rag_semcache_hits_total[5m])
/ (rate(ollama_rag_semcache_hits_total[5m]) + rate(ollama_rag_semcache_misses_total[5m]))
```

### Health Queries

```promql
# Is circuit breaker healthy? (0 = yes)
ollama_rag_circuit_breaker_state

# Time since circuit last changed state (seconds)
time() - ollama_rag_circuit_breaker_last_state_change_timestamp

# Current consecutive failures
ollama_rag_circuit_breaker_consecutive_failures
```

### Capacity Queries

```promql
# Cache utilization percentage
100 * ollama_rag_semcache_fill_ratio

# Cache size
ollama_rag_semcache_size

# Connection pool configuration
ollama_rag_connection_pool_size
```

---

## 🔍 Troubleshooting

### Circuit Breaker Keeps Opening

**Check**:
```promql
# Recent failures
rate(ollama_rag_circuit_breaker_calls_total{status="failure"}[1m])

# Consecutive failures
ollama_rag_circuit_breaker_consecutive_failures
```

**Solutions**:
1. Check Ollama service health
2. Review error logs
3. Increase failure threshold if false positives
4. Check network connectivity

### Low Cache Hit Rate

**Check**:
```promql
# Current hit rate
rate(ollama_rag_semcache_hits_total[5m])
/ (rate(ollama_rag_semcache_hits_total[5m]) + rate(ollama_rag_semcache_misses_total[5m]))

# Cache size vs max
ollama_rag_semcache_fill_ratio
```

**Solutions**:
1. Lower similarity threshold (0.90 instead of 0.95)
2. Increase cache size
3. Increase TTL
4. Enable cache warming

### High Request Rate

**Check**:
```promql
# Requests per second
rate(ollama_rag_connection_pool_requests_total[1m])
```

**Solutions**:
1. Enable caching
2. Increase connection pool size
3. Add rate limiting
4. Scale horizontally

---

## 🎯 Best Practices

### 1. Monitoring Setup

✅ **DO**:
- Scrape metrics every 15-30 seconds
- Set up alerts for critical metrics
- Monitor trends over time
- Create dashboards for visibility

❌ **DON'T**:
- Scrape too frequently (<5s)
- Ignore warning alerts
- Only check when issues occur

### 2. Alert Configuration

✅ **DO**:
- Use `for` duration to avoid alert fatigue
- Set appropriate thresholds
- Include actionable annotations
- Test alerts before production

❌ **DON'T**:
- Alert on every small spike
- Use overly sensitive thresholds
- Forget to test alert rules

### 3. Dashboard Design

✅ **DO**:
- Group related metrics
- Use appropriate visualization types
- Add descriptions/annotations
- Keep dashboards focused

❌ **DON'T**:
- Cram too many panels
- Use confusing colors
- Mix unrelated metrics

---

## 📚 Additional Resources

### Endpoints

- **Prometheus Metrics**: `GET /metrics`
- **Cache Stats (JSON)**: `GET /api/cache-stats`
- **Health Check**: `GET /health` (if implemented)

### Documentation

- Sprint 2 Progress: `docs/SPRINT2_DAY1_PROGRESS.md`
- Sprint 2 Day 2: `docs/SPRINT2_DAY2_PROGRESS.md`
- Caching Guide: `docs/CACHING.md`

### Configuration

Metrics are enabled by default. No configuration needed!

---

## 🎊 Success Metrics

Your monitoring is successful when you can:

✅ Detect circuit breaker opens in real-time
✅ Track request success/failure rates
✅ Monitor cache effectiveness
✅ Identify performance degradation early
✅ Make data-driven optimization decisions

---

**Guide Version**: 1.0
**Last Updated**: 2025-10-06
**Status**: ✅ Production Ready

---

*"From metrics to insights - monitor like a pro!"* 📊🚀
