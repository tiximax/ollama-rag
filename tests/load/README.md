# 🔥 Load Testing Suite - Sprint 3

**Status**: Production Ready
**Version**: 1.0.0
**Vibe**: Testing như một rockstar! 🎸

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Test Scenarios](#test-scenarios)
4. [Metrics Collection](#metrics-collection)
5. [Running Tests](#running-tests)
6. [Analyzing Results](#analyzing-results)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

Complete load testing suite để validate Sprint 2 metrics dashboard under stress!

**What We Test:**
- ✅ Ollama RAG system under realistic load
- ✅ Circuit breaker triggers and recovery
- ✅ Connection pool saturation
- ✅ Cache effectiveness
- ✅ All 11 Prometheus metrics

**Tools:**
- **Locust**: Load testing framework
- **Prometheus**: Metrics collection
- **Custom Metrics Collector**: Real-time monitoring

---

## 🚀 Quick Start

### Prerequisites

```powershell
# Verify Locust installed
python -c "import locust; print(locust.__version__)"
# Expected: 2.17.0+

# Verify FastAPI app running
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### 1-Minute Test

```powershell
# Terminal 1: Start your FastAPI app
python app/main.py

# Terminal 2: Run quick load test (Web UI)
cd tests/load
locust -f locustfile.py --host=http://localhost:8000

# Open browser: http://localhost:8089
# Settings:
#   - Number of users: 10
#   - Spawn rate: 2
#   - Duration: 1 minute
# Click "Start swarming"!
```

---

## 🎭 Test Scenarios

### Available Scenarios

| Scenario | Users | Duration | Purpose |
|----------|-------|----------|---------|
| **Normal Load** | 50 | 5 min | Baseline traffic |
| **Spike Test** | 200 | 3 min | Traffic spike (Black Friday!) |
| **Stress Test** | 500 | 10 min | Find breaking point |
| **Soak Test** | 100 | 30 min | Detect memory leaks |
| **Circuit Breaker** | 300 | 2 min | Validate failover |

### Scenario Details

#### 1. Normal Load (Baseline)
```powershell
locust -f scenarios.py `
       --host=http://localhost:8000 `
       --users 50 `
       --spawn-rate 5 `
       --run-time 5m `
       --headless `
       --html reports/normal_load_report.html
```

**Expected Results:**
- 0-5% error rate
- Circuit breaker: CLOSED
- Pool usage: <50%
- Cache hit rate: 70-85%

#### 2. Spike Test
```powershell
locust -f scenarios.py `
       --host=http://localhost:8000 `
       --users 200 `
       --spawn-rate 50 `
       --run-time 3m `
       --headless `
       --html reports/spike_test_report.html
```

**Expected Results:**
- 10-20% error rate during spike
- Circuit breaker: May OPEN temporarily
- Pool usage: 80-100%
- Cache hit rate: 60-75%

#### 3. Stress Test
```powershell
locust -f scenarios.py `
       --host=http://localhost:8000 `
       --users 500 `
       --spawn-rate 10 `
       --run-time 10m `
       --headless `
       --html reports/stress_test_report.html
```

**Expected Results:**
- 20-40% error rate at peak
- Circuit breaker: OPEN during stress
- Pool usage: 100% (saturated)
- System breaking point identified

#### 4. Soak Test
```powershell
locust -f scenarios.py `
       --host=http://localhost:8000 `
       --users 100 `
       --spawn-rate 5 `
       --run-time 30m `
       --headless `
       --html reports/soak_test_report.html
```

**Expected Results:**
- Stable error rate (<10%)
- No memory leaks
- Consistent latency over time
- Circuit breaker: Stable state

#### 5. Circuit Breaker Validation
```powershell
locust -f scenarios.py `
       --host=http://localhost:8000 `
       --users 300 `
       --spawn-rate 100 `
       --run-time 2m `
       --headless `
       --html reports/circuit_breaker_test_report.html
```

**Expected Results:**
- Circuit breaker: OPEN → HALF_OPEN → CLOSED cycle
- Fast-fail responses (503)
- Recovery within 60 seconds

---

## 📊 Metrics Collection

### Real-time Monitoring

Run metrics collector in parallel với load test:

```powershell
# Terminal 1: Start FastAPI app
python app/main.py

# Terminal 2: Start metrics collector
cd tests/load
python metrics_collector.py --interval 1.0

# Terminal 3: Run load test
locust -f locustfile.py --host=http://localhost:8000
```

### Collected Metrics

- **Requests**: Total, success, failure, in-progress
- **Latency**: Sum, count, average
- **Circuit Breaker**: State, failures
- **Connection Pool**: Active, idle, total, wait time
- **Cache**: Hits, misses, size, hit rate

### Output

Metrics saved to: `tests/load/reports/metrics_YYYYMMDD_HHMMSS.json`

```json
{
  "collection_metadata": {
    "start_time": "2025-10-06 13:00:00",
    "end_time": "2025-10-06 13:05:00",
    "total_snapshots": 300,
    "collection_interval": 1.0
  },
  "snapshots": [ ... ]
}
```

---

## 🎬 Running Tests

### Web UI Mode (Recommended for Exploration)

```powershell
cd tests/load
locust -f locustfile.py --host=http://localhost:8000

# Open browser: http://localhost:8089
# Configure:
#   - Number of users (peak concurrency)
#   - Spawn rate (users/second)
#   - Run time (optional)
# Click "Start swarming"!
```

**Pros:**
- Real-time graphs
- Easy control (start/stop)
- Download CSV/stats

### Headless Mode (Recommended for CI/CD)

```powershell
# Run predefined scenario
locust -f scenarios.py `
       --host=http://localhost:8000 `
       --users 100 `
       --spawn-rate 10 `
       --run-time 5m `
       --headless `
       --html reports/test_report.html `
       --csv reports/test_data
```

**Pros:**
- Automated
- Scriptable
- CI/CD friendly

### Distributed Mode (For High Load)

```powershell
# Terminal 1: Master
locust -f locustfile.py --master --host=http://localhost:8000

# Terminal 2-N: Workers
locust -f locustfile.py --worker --master-host=localhost

# Open master UI: http://localhost:8089
```

**Use Case**: Simulate 1000+ users beyond single machine capacity!

---

## 📈 Analyzing Results

### Locust HTML Report

Generated at: `tests/load/reports/<scenario>_report.html`

**Key Sections:**
1. **Statistics**: Request counts, latency percentiles
2. **Charts**: RPS, latency over time, user count
3. **Failures**: Error details
4. **Download**: CSV for further analysis

### Metrics JSON Analysis

```powershell
# Analyze collected metrics
python -c "
import json
with open('reports/metrics_20251006_130000.json') as f:
    data = json.load(f)

# Print summary
print(f'Duration: {data[\"collection_metadata\"][\"end_time\"]}')
print(f'Snapshots: {data[\"collection_metadata\"][\"total_snapshots\"]}')
"
```

### Key Metrics to Check

#### 1. Circuit Breaker Validation
```python
# Check if circuit breaker triggered
cb_states = [s["circuit_breaker"]["state"] for s in data["snapshots"]]
opens = cb_states.count(1)  # OPEN state
print(f"Circuit breaker opened {opens} times")
```

#### 2. Connection Pool Saturation
```python
# Check peak pool usage
pool_usages = [s["connection_pool"]["active"] for s in data["snapshots"]]
peak = max(pool_usages)
print(f"Peak pool usage: {peak} connections")
```

#### 3. Cache Effectiveness
```python
# Calculate overall cache hit rate
first = data["snapshots"][0]
last = data["snapshots"][-1]
hits = last["cache"]["hits"] - first["cache"]["hits"]
misses = last["cache"]["misses"] - first["cache"]["misses"]
hit_rate = hits / (hits + misses) * 100
print(f"Cache hit rate: {hit_rate:.2f}%")
```

---

## 🐛 Troubleshooting

### Issue: Locust won't start

**Symptoms:**
```
ModuleNotFoundError: No module named 'locust'
```

**Solution:**
```powershell
pip install locust==2.17.0
```

---

### Issue: Can't connect to FastAPI app

**Symptoms:**
```
ConnectionError: HTTPConnectionPool(host='localhost', port=8000)
```

**Solution:**
```powershell
# Check if app is running
curl http://localhost:8000/health

# If not, start it:
python app/main.py
```

---

### Issue: All requests fail with 503

**Symptoms:**
- 100% requests return 503
- Circuit breaker stuck in OPEN

**Solution:**
1. Check Ollama service is running:
   ```powershell
   ollama list
   ```

2. Restart circuit breaker:
   ```powershell
   # Stop load test
   # Wait 60 seconds (timeout)
   # Restart test with lower users
   ```

3. Adjust circuit breaker config in `.env`:
   ```env
   CIRCUIT_BREAKER_FAILURE_THRESHOLD=10  # Increase tolerance
   CIRCUIT_BREAKER_TIMEOUT=30  # Shorter recovery
   ```

---

### Issue: Metrics collector shows 0 for all metrics

**Symptoms:**
```json
{
  "requests_total": 0,
  "requests_success": 0,
  ...
}
```

**Solution:**
1. Verify `/metrics` endpoint:
   ```powershell
   curl http://localhost:8000/metrics
   ```

2. Check metric names match:
   ```python
   # In metrics_collector.py, ensure patterns match actual metric names
   snapshot.requests_total = int(extract_metric(r'ollama_requests_total\s+([\d.]+)') or 0)
   ```

---

### Issue: Load test runs too slow

**Symptoms:**
- Spawn rate < expected
- User count doesn't ramp up

**Solution:**
1. Reduce wait time in User classes:
   ```python
   wait_time = between(0.5, 1)  # Faster
   ```

2. Increase spawn rate:
   ```powershell
   --spawn-rate 50  # Was 10
   ```

3. Use distributed mode for high concurrency

---

## 🎯 Best Practices

### Before Running Load Tests

1. **Baseline**: Run normal load first to establish baseline
2. **Monitoring**: Always run metrics collector in parallel
3. **Incremental**: Start small (10 users), then scale up
4. **Duration**: Minimum 2 minutes for meaningful results

### During Load Tests

1. **Watch Metrics**: Monitor circuit breaker state, pool usage
2. **Take Notes**: Document observations (e.g., "CB opened at 150 users")
3. **Screenshots**: Capture Locust UI at peak load

### After Load Tests

1. **Analyze**: Review HTML report + metrics JSON
2. **Compare**: Compare with baseline
3. **Document**: Update findings in Sprint 3 report
4. **Iterate**: Adjust configs and re-test

---

## 📚 Additional Resources

### Locust Documentation
- Official Docs: https://docs.locust.io/
- Best Practices: https://docs.locust.io/en/stable/running-distributed.html

### Prometheus Metrics
- See: `docs/METRICS_MONITORING.md`
- Dashboard: `docs/grafana_dashboard.json`

### Sprint 3 Planning
- See: `docs/SPRINT3_PLAN.md` (to be created)

---

## 🎉 Success Criteria

Load testing is successful when:

✅ **Normal Load**: <5% error rate, circuit breaker CLOSED
✅ **Spike Test**: Circuit breaker triggers and recovers
✅ **Stress Test**: Breaking point identified (e.g., 400 users)
✅ **Soak Test**: Stable for 30+ minutes, no memory leaks
✅ **Metrics**: All 11 metrics tracked accurately

---

## 🚀 Next Steps

After completing load tests:

1. **Create Sprint 3 Report**: Document findings
2. **Optimize Configs**: Adjust based on results
3. **Grafana Dashboard**: Import and visualize
4. **PR Review**: Submit Sprint 3 changes

---

**Vibe**: You're now a load testing rockstar! 🎸💎

*Happy testing! 🔥*
