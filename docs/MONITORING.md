# 📈 Monitoring & Observability Guide

This guide shows how to enable, monitor, and alert on the Ollama RAG service in production.

## Endpoints
- GET /metrics
  - Prometheus metrics endpoint
  - Content-Type: text/plain; version=0.0.4
- GET /api/cache-stats
  - Human-friendly JSON cache statistics
- GET /health
  - Service/system health summary

## Prometheus Setup
1. Add a scrape job for FastAPI server (default port 8000):
```yaml
scrape_configs:
  - job_name: 'ollama_rag'
    static_configs:
      - targets: ['localhost:8000']
```
2. Load alert rules:
```yaml
rule_files:
  - 'monitoring/alerts.yml'
```
3. Reload Prometheus:
```bash
curl -X POST http://localhost:9090/-/reload
```

## Grafana Dashboard
- Import from file monitoring/grafana-dashboard.json
- Set data source to your Prometheus

### Panels included
- Query Rate (req/s)
- Response Time (P50/P95/P99)
- Cache Hit Rate
- Error Rate
- Service Health
- Retrieval & Reranking Performance
- System CPU/Memory
- HTTP by Status

## Key Metrics (examples)
- ollama_rag_queries_total{method,provider,db}
- ollama_rag_llm_response_seconds_bucket
- ollama_rag_retrieval_seconds_bucket
- ollama_rag_rerank_seconds_bucket
- ollama_rag_query_errors_total{error}
- ollama_rag_system_cpu_percent
- ollama_rag_system_memory_percent
- ollama_rag_db_size_bytes

## Alerts
See monitoring/alerts.yml (12 rules):
- HighQueryErrorRate
- VerySlowQueries
- ServiceUnhealthy
- OllamaServiceDown
- HighMemoryUsage
- SlowRetrieval
- SlowReranking
- LowCacheHitRate
- HighRequestRate
- LargeDatabaseSize

## Tips
- Always expose /metrics behind auth if deployed publicly
- Use CORS whitelist for /api/** endpoints
- Attach X-Request-ID to logs for traceability
