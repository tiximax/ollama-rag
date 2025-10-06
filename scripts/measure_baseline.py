"""
Baseline Performance Measurement Script
========================================
Script siêu thông minh để đo hiệu suất hiện tại của Ollama RAG system! 🚀

Đo các metrics quan trọng:
- Response Time (P50, P95, P99)
- Throughput (requests/second)
- Error Rate
- Resource Usage (CPU, Memory)
- Connection Pool Stats
"""

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
import requests

# === Configuration ===
BASE_URL = "http://localhost:8001"  # Port 8001 theo start_server.py
NUM_REQUESTS = 100  # Số lượng requests để test
CONCURRENT_REQUESTS = 10  # Số requests đồng thời
WARMUP_REQUESTS = 10  # Số requests khởi động

# Sample test queries
TEST_QUERIES = [
    "What is machine learning?",
    "Explain neural networks",
    "How does RAG work?",
    "What is deep learning?",
    "Define artificial intelligence",
]


class BaselineMetrics:
    """Class để lưu trữ và tính toán metrics như một rockstar! 💎"""

    def __init__(self):
        self.response_times: list[float] = []
        self.error_count = 0
        self.total_requests = 0
        self.start_time = None
        self.end_time = None

    def add_response_time(self, rt: float):
        """Thêm response time - chính xác như kim cương! 💎"""
        self.response_times.append(rt)

    def increment_error(self):
        """Đếm lỗi - tracking như pro! 🎯"""
        self.error_count += 1

    def increment_requests(self):
        """Đếm requests - không bỏ sót! ✅"""
        self.total_requests += 1

    def calculate_percentiles(self) -> dict[str, float]:
        """Tính percentiles - chuẩn như công thức vàng! 📊"""
        if not self.response_times:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}

        sorted_times = sorted(self.response_times)
        return {
            "p50": (
                statistics.quantiles(sorted_times, n=100)[49]
                if len(sorted_times) > 1
                else sorted_times[0]
            ),
            "p95": (
                statistics.quantiles(sorted_times, n=100)[94]
                if len(sorted_times) > 1
                else sorted_times[0]
            ),
            "p99": (
                statistics.quantiles(sorted_times, n=100)[98]
                if len(sorted_times) > 1
                else sorted_times[0]
            ),
            "mean": statistics.mean(sorted_times),
            "min": min(sorted_times),
            "max": max(sorted_times),
        }

    def calculate_throughput(self) -> float:
        """Tính throughput - requests/second như tên lửa! 🚀"""
        if not self.start_time or not self.end_time:
            return 0.0
        duration = self.end_time - self.start_time
        return self.total_requests / duration if duration > 0 else 0.0

    def calculate_error_rate(self) -> float:
        """Tính error rate - phần trăm lỗi! ⚠️"""
        if self.total_requests == 0:
            return 0.0
        return (self.error_count / self.total_requests) * 100

    def get_summary(self) -> dict[str, Any]:
        """Tạo summary ổn định như núi! 🏔️"""
        percentiles = self.calculate_percentiles()
        return {
            "timestamp": datetime.now().isoformat(),
            "total_requests": self.total_requests,
            "successful_requests": self.total_requests - self.error_count,
            "error_count": self.error_count,
            "error_rate_percent": round(self.calculate_error_rate(), 2),
            "throughput_rps": round(self.calculate_throughput(), 2),
            "response_times_ms": {
                "p50": round(percentiles["p50"] * 1000, 2),
                "p95": round(percentiles["p95"] * 1000, 2),
                "p99": round(percentiles["p99"] * 1000, 2),
                "mean": round(percentiles["mean"] * 1000, 2),
                "min": round(percentiles["min"] * 1000, 2),
                "max": round(percentiles["max"] * 1000, 2),
            },
            "duration_seconds": (
                round(self.end_time - self.start_time, 2)
                if self.start_time and self.end_time
                else 0.0
            ),
        }


def get_resource_usage() -> dict[str, float]:
    """
    Lấy thông tin resource usage - CPU và Memory! 💻
    Tracking như pro để không bỏ sót gì!
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": round(memory.available / (1024 * 1024), 2),
        }
    except Exception as e:
        print(f"⚠️  Warning: Không thể lấy resource usage: {e}")
        return {"cpu_percent": 0.0, "memory_percent": 0.0, "memory_available_mb": 0.0}


def make_request(query: str, timeout: int = 30) -> dict[str, Any]:
    """
    Thực hiện single request với error handling như siêu anh hùng! 🦸‍♂️

    Returns:
        Dict với keys: success (bool), response_time (float), error (str hoặc None)
    """
    start_time = time.time()
    try:
        # Call /api/query endpoint với payload phù hợp
        response = requests.post(
            f"{BASE_URL}/api/query",  # Endpoint chính xác
            json={
                "query": query,
                "k": 5,
                "method": "vector",
                "rerank_enable": False,
                "save_chat": False,
            },
            timeout=timeout,
        )
        response_time = time.time() - start_time

        if response.status_code == 200:
            return {"success": True, "response_time": response_time, "error": None}
        else:
            return {
                "success": False,
                "response_time": response_time,
                "error": f"HTTP {response.status_code}",
            }
    except requests.exceptions.Timeout:
        response_time = time.time() - start_time
        return {"success": False, "response_time": response_time, "error": "Timeout"}
    except Exception as e:
        response_time = time.time() - start_time
        return {"success": False, "response_time": response_time, "error": str(e)}


def run_warmup():
    """
    Chạy warmup requests để khởi động hệ thống! 🔥
    Giống như khởi động trước khi chạy marathon!
    """
    print(f"🔥 Warmup: Chạy {WARMUP_REQUESTS} requests...")
    for i in range(WARMUP_REQUESTS):
        query = TEST_QUERIES[i % len(TEST_QUERIES)]
        result = make_request(query)
        if result["success"]:
            print(f"  ✅ Warmup {i+1}/{WARMUP_REQUESTS}")
        else:
            print(f"  ⚠️  Warmup {i+1}/{WARMUP_REQUESTS} failed: {result['error']}")
    print("🔥 Warmup completed!\n")


def run_baseline_test() -> BaselineMetrics:
    """
    Chạy baseline test với concurrent requests như rockstar! 🎸
    Sử dụng ThreadPoolExecutor để tạo tải đồng thời!
    """
    metrics = BaselineMetrics()

    print("🚀 Bắt đầu baseline test:")
    print(f"   - Total requests: {NUM_REQUESTS}")
    print(f"   - Concurrent requests: {CONCURRENT_REQUESTS}\n")

    metrics.start_time = time.time()

    # Sử dụng ThreadPoolExecutor để chạy concurrent requests
    with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        # Submit all requests
        futures = []
        for i in range(NUM_REQUESTS):
            query = TEST_QUERIES[i % len(TEST_QUERIES)]
            future = executor.submit(make_request, query)
            futures.append(future)

        # Collect results khi hoàn thành
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            metrics.increment_requests()

            if result["success"]:
                metrics.add_response_time(result["response_time"])
            else:
                metrics.increment_error()
                print(f"  ❌ Request failed: {result['error']}")

            completed += 1
            if completed % 10 == 0:
                print(f"  📊 Progress: {completed}/{NUM_REQUESTS} requests completed")

    metrics.end_time = time.time()
    print("\n✅ Baseline test completed!\n")

    return metrics


def save_results(metrics: BaselineMetrics, resource_usage: dict[str, float]):
    """Lưu kết quả vào file JSON - dữ liệu ổn định như kim cương! 💎"""
    results = {
        "test_info": {
            "test_name": "baseline_measurement",
            "num_requests": NUM_REQUESTS,
            "concurrent_requests": CONCURRENT_REQUESTS,
            "base_url": BASE_URL,
        },
        "metrics": metrics.get_summary(),
        "resource_usage": resource_usage,
    }

    # Tạo output directory nếu chưa có
    output_dir = Path("tests/baseline")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save với timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"baseline_results_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"💾 Kết quả đã lưu: {output_file}")
    return output_file


def print_summary(metrics: BaselineMetrics, resource_usage: dict[str, float]):
    """In summary đẹp như tranh vẽ! 🎨"""
    summary = metrics.get_summary()

    print("=" * 60)
    print("📊 BASELINE PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"⏱️  Total Duration: {summary['duration_seconds']} seconds")
    print(f"📨 Total Requests: {summary['total_requests']}")
    print(f"✅ Successful: {summary['successful_requests']}")
    print(f"❌ Errors: {summary['error_count']} ({summary['error_rate_percent']}%)")
    print(f"🚀 Throughput: {summary['throughput_rps']} req/sec")
    print()
    print("⏱️  Response Times (ms):")
    print(f"   - Mean: {summary['response_times_ms']['mean']}")
    print(f"   - P50:  {summary['response_times_ms']['p50']}")
    print(f"   - P95:  {summary['response_times_ms']['p95']}")
    print(f"   - P99:  {summary['response_times_ms']['p99']}")
    print(f"   - Min:  {summary['response_times_ms']['min']}")
    print(f"   - Max:  {summary['response_times_ms']['max']}")
    print()
    print("💻 Resource Usage:")
    print(f"   - CPU: {resource_usage['cpu_percent']}%")
    print(f"   - Memory: {resource_usage['memory_percent']}%")
    print(f"   - Available Memory: {resource_usage['memory_available_mb']} MB")
    print("=" * 60)


def main():
    """Main function - điều khiển toàn bộ flow như conductor! 🎼"""
    print("\n" + "=" * 60)
    print("🎯 OLLAMA RAG BASELINE PERFORMANCE MEASUREMENT")
    print("=" * 60 + "\n")

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"⚠️  Warning: Server health check failed (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Error: Cannot connect to server at {BASE_URL}")
        print("   Please start the server first!")
        print(f"   Error: {e}")
        return

    # Run warmup
    run_warmup()

    # Run baseline test
    metrics = run_baseline_test()

    # Get resource usage
    resource_usage = get_resource_usage()

    # Print summary
    print_summary(metrics, resource_usage)

    # Save results
    output_file = save_results(metrics, resource_usage)

    print("\n🎉 Baseline measurement completed successfully!")
    print(f"📄 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
