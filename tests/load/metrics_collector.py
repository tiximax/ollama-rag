"""
📊 Real-time Metrics Collector - Sprint 3 Day 1
===============================================

Collect Prometheus metrics trong lúc load testing để phân tích sau!

Features:
- Poll Prometheus /metrics endpoint
- Parse và lưu metrics theo timeline
- Tạo graphs để visualize metrics under load
- Detect anomalies (circuit breaker triggers, pool exhaustion)

Vibe: Track metrics như detective! 🕵️
"""

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

# ============================================================================
# 📊 Metrics Data Models
# ============================================================================


@dataclass
class MetricSnapshot:
    """
    Snapshot của metrics tại một thời điểm

    Lưu trữ dữ liệu như photographer chụp ảnh! 📸
    """

    timestamp: float
    datetime_str: str

    # Request metrics
    requests_total: int = 0
    requests_success: int = 0
    requests_failure: int = 0
    requests_in_progress: int = 0

    # Latency metrics (seconds)
    latency_sum: float = 0.0
    latency_count: int = 0

    # Circuit breaker metrics
    circuit_breaker_state: int = 0  # 0=CLOSED, 1=OPEN, 2=HALF_OPEN
    circuit_breaker_failures: int = 0

    # Connection pool metrics
    pool_active_connections: int = 0
    pool_idle_connections: int = 0
    pool_total_connections: int = 0
    pool_wait_time_sum: float = 0.0
    pool_wait_time_count: int = 0

    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size: int = 0

    def to_dict(self) -> dict:
        """Convert to dict cho JSON serialization"""
        return {
            "timestamp": self.timestamp,
            "datetime": self.datetime_str,
            "requests": {
                "total": self.requests_total,
                "success": self.requests_success,
                "failure": self.requests_failure,
                "in_progress": self.requests_in_progress,
            },
            "latency": {
                "sum": self.latency_sum,
                "count": self.latency_count,
                "avg": self.latency_sum / self.latency_count if self.latency_count > 0 else 0,
            },
            "circuit_breaker": {
                "state": self.circuit_breaker_state,
                "state_name": ["CLOSED", "OPEN", "HALF_OPEN"][self.circuit_breaker_state],
                "failures": self.circuit_breaker_failures,
            },
            "connection_pool": {
                "active": self.pool_active_connections,
                "idle": self.pool_idle_connections,
                "total": self.pool_total_connections,
                "wait_time_avg": (
                    self.pool_wait_time_sum / self.pool_wait_time_count
                    if self.pool_wait_time_count > 0
                    else 0
                ),
            },
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "size": self.cache_size,
                "hit_rate": (
                    self.cache_hits / (self.cache_hits + self.cache_misses)
                    if (self.cache_hits + self.cache_misses) > 0
                    else 0
                ),
            },
        }


# ============================================================================
# 📊 Metrics Collector
# ============================================================================


class PrometheusMetricsCollector:
    """
    Collector ổn định như kim cương! 💎

    Collect metrics định kỳ và lưu vào file để phân tích!
    """

    def __init__(
        self,
        metrics_url: str = "http://localhost:8000/metrics",
        collection_interval: float = 1.0,  # seconds
        output_dir: str = "tests/load/reports",
    ):
        """
        Initialize collector với config ổn định!

        Args:
            metrics_url: URL của Prometheus metrics endpoint
            collection_interval: Khoảng thời gian giữa các lần collect (seconds)
            output_dir: Thư mục lưu reports
        """
        self.metrics_url = metrics_url
        self.collection_interval = collection_interval
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.snapshots: list[MetricSnapshot] = []
        self.is_collecting = False

        print("📊 Metrics Collector initialized:")
        print(f"   URL: {metrics_url}")
        print(f"   Interval: {collection_interval}s")
        print(f"   Output: {output_dir}")

    def parse_prometheus_metrics(self, metrics_text: str) -> MetricSnapshot:
        """
        Parse Prometheus text format thành MetricSnapshot

        Regex parsing như một parser pro! 🎯
        """
        timestamp = time.time()
        datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        snapshot = MetricSnapshot(timestamp=timestamp, datetime_str=datetime_str)

        # Helper function để extract metric value
        def extract_metric(pattern: str) -> float | None:
            match = re.search(pattern, metrics_text)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    return None
            return None

        # Extract requests metrics
        snapshot.requests_total = int(extract_metric(r'ollama_requests_total\s+([\d.]+)') or 0)
        snapshot.requests_success = int(
            extract_metric(r'ollama_requests_total\{.*status="success".*\}\s+([\d.]+)') or 0
        )
        snapshot.requests_failure = int(
            extract_metric(r'ollama_requests_total\{.*status="error".*\}\s+([\d.]+)') or 0
        )
        snapshot.requests_in_progress = int(
            extract_metric(r'ollama_requests_in_progress\s+([\d.]+)') or 0
        )

        # Extract latency metrics
        snapshot.latency_sum = (
            extract_metric(r'ollama_request_latency_seconds_sum\s+([\d.]+)') or 0.0
        )
        snapshot.latency_count = int(
            extract_metric(r'ollama_request_latency_seconds_count\s+([\d.]+)') or 0
        )

        # Extract circuit breaker metrics
        snapshot.circuit_breaker_state = int(
            extract_metric(r'circuit_breaker_state\s+([\d.]+)') or 0
        )
        snapshot.circuit_breaker_failures = int(
            extract_metric(r'circuit_breaker_failures_total\s+([\d.]+)') or 0
        )

        # Extract connection pool metrics
        snapshot.pool_active_connections = int(
            extract_metric(r'connection_pool_active_connections\s+([\d.]+)') or 0
        )
        snapshot.pool_idle_connections = int(
            extract_metric(r'connection_pool_idle_connections\s+([\d.]+)') or 0
        )
        snapshot.pool_total_connections = int(
            extract_metric(r'connection_pool_total_connections\s+([\d.]+)') or 0
        )
        snapshot.pool_wait_time_sum = (
            extract_metric(r'connection_pool_wait_time_seconds_sum\s+([\d.]+)') or 0.0
        )
        snapshot.pool_wait_time_count = int(
            extract_metric(r'connection_pool_wait_time_seconds_count\s+([\d.]+)') or 0
        )

        # Extract cache metrics
        snapshot.cache_hits = int(extract_metric(r'cache_hits_total\s+([\d.]+)') or 0)
        snapshot.cache_misses = int(extract_metric(r'cache_misses_total\s+([\d.]+)') or 0)
        snapshot.cache_size = int(extract_metric(r'cache_size_bytes\s+([\d.]+)') or 0)

        return snapshot

    def collect_once(self) -> MetricSnapshot | None:
        """
        Collect metrics một lần duy nhất

        Returns:
            MetricSnapshot hoặc None nếu lỗi
        """
        try:
            response = requests.get(self.metrics_url, timeout=5)
            if response.status_code == 200:
                snapshot = self.parse_prometheus_metrics(response.text)
                self.snapshots.append(snapshot)
                return snapshot
            else:
                print(f"❌ Failed to fetch metrics: HTTP {response.status_code}")
                return None

        except requests.RequestException as e:
            print(f"❌ Metrics collection error: {e}")
            return None

    def start_continuous_collection(self):
        """
        Bắt đầu collect metrics liên tục

        Chạy trong background như service! 🚀
        """
        self.is_collecting = True
        print(f"🚀 Starting continuous metrics collection (interval: {self.collection_interval}s)")
        print("   Press Ctrl+C to stop")

        try:
            while self.is_collecting:
                snapshot = self.collect_once()

                if snapshot:
                    # Print summary
                    print(
                        f"📊 [{snapshot.datetime_str}] "
                        f"Requests: {snapshot.requests_total} | "
                        f"CB: {['CLOSED', 'OPEN', 'HALF_OPEN'][snapshot.circuit_breaker_state]} | "
                        f"Pool: {snapshot.pool_active_connections}/{snapshot.pool_total_connections} | "
                        f"Cache Hit: {snapshot.cache_hits/(snapshot.cache_hits + snapshot.cache_misses)*100 if (snapshot.cache_hits + snapshot.cache_misses) > 0 else 0:.1f}%"
                    )

                time.sleep(self.collection_interval)

        except KeyboardInterrupt:
            print("\n⚠️ Collection stopped by user")
            self.stop_collection()

    def stop_collection(self):
        """Stop collection và save data"""
        self.is_collecting = False
        self.save_snapshots()
        print(f"✅ Collection stopped. Total snapshots: {len(self.snapshots)}")

    def save_snapshots(self, filename: str | None = None):
        """
        Lưu snapshots vào JSON file

        Args:
            filename: Tên file (mặc định: metrics_{timestamp}.json)
        """
        if not self.snapshots:
            print("⚠️ No snapshots to save")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.json"

        output_path = self.output_dir / filename

        # Convert snapshots to dict
        data = {
            "collection_metadata": {
                "start_time": self.snapshots[0].datetime_str if self.snapshots else None,
                "end_time": self.snapshots[-1].datetime_str if self.snapshots else None,
                "total_snapshots": len(self.snapshots),
                "collection_interval": self.collection_interval,
            },
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"💾 Metrics saved to: {output_path}")
        return output_path

    def analyze_snapshots(self) -> dict:
        """
        Phân tích snapshots để tìm insights!

        Returns:
            Dictionary với analysis results
        """
        if not self.snapshots:
            return {"error": "No snapshots to analyze"}

        # Calculate aggregates
        total_requests = self.snapshots[-1].requests_total - self.snapshots[0].requests_total
        total_failures = self.snapshots[-1].requests_failure - self.snapshots[0].requests_failure

        # Find circuit breaker triggers
        cb_triggers = sum(
            1
            for i in range(1, len(self.snapshots))
            if self.snapshots[i].circuit_breaker_state == 1  # OPEN
            and self.snapshots[i - 1].circuit_breaker_state == 0
        )  # Was CLOSED

        # Find peak pool usage
        peak_pool_usage = max(s.pool_active_connections for s in self.snapshots)
        max_pool_size = max(s.pool_total_connections for s in self.snapshots)

        # Calculate average cache hit rate
        total_cache_hits = self.snapshots[-1].cache_hits - self.snapshots[0].cache_hits
        total_cache_misses = self.snapshots[-1].cache_misses - self.snapshots[0].cache_misses
        cache_hit_rate = (
            total_cache_hits / (total_cache_hits + total_cache_misses)
            if (total_cache_hits + total_cache_misses) > 0
            else 0
        )

        analysis = {
            "summary": {
                "duration_seconds": self.snapshots[-1].timestamp - self.snapshots[0].timestamp,
                "total_snapshots": len(self.snapshots),
                "total_requests": total_requests,
                "failure_rate": total_failures / total_requests if total_requests > 0 else 0,
            },
            "circuit_breaker": {
                "triggers_detected": cb_triggers,
                "final_state": ["CLOSED", "OPEN", "HALF_OPEN"][
                    self.snapshots[-1].circuit_breaker_state
                ],
            },
            "connection_pool": {
                "peak_usage": peak_pool_usage,
                "max_size": max_pool_size,
                "utilization_percent": (
                    (peak_pool_usage / max_pool_size * 100) if max_pool_size > 0 else 0
                ),
            },
            "cache": {
                "hit_rate": cache_hit_rate * 100,
                "total_hits": total_cache_hits,
                "total_misses": total_cache_misses,
            },
        }

        return analysis


# ============================================================================
# 🎬 CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    """
    Standalone metrics collector cho load tests!

    Usage:
        # Collect metrics trong 60 seconds:
        python metrics_collector.py

        # Custom interval:
        python metrics_collector.py --interval 0.5

        # Custom URL:
        python metrics_collector.py --url http://localhost:9000/metrics
    """
    import argparse

    parser = argparse.ArgumentParser(description="Prometheus Metrics Collector for Load Tests")
    parser.add_argument(
        "--url", default="http://localhost:8000/metrics", help="Metrics endpoint URL"
    )
    parser.add_argument(
        "--interval", type=float, default=1.0, help="Collection interval in seconds"
    )
    parser.add_argument(
        "--output-dir", default="tests/load/reports", help="Output directory for reports"
    )

    args = parser.parse_args()

    print(
        """
╔═══════════════════════════════════════════════════════════════╗
║  📊 Prometheus Metrics Collector - Sprint 3
╚═══════════════════════════════════════════════════════════════╝
    """
    )

    collector = PrometheusMetricsCollector(
        metrics_url=args.url,
        collection_interval=args.interval,
        output_dir=args.output_dir,
    )

    # Start collection
    collector.start_continuous_collection()

    # Analyze results
    print("\n📊 Analyzing collected metrics...")
    analysis = collector.analyze_snapshots()

    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║  📊 ANALYSIS RESULTS")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print(json.dumps(analysis, indent=2))

    print("\n✅ Metrics collection complete! Vibe: Tracking như pro! 🎸")
