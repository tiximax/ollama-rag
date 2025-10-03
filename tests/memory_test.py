"""
Simple memory leak test cho Ollama RAG.

Test này verify rằng resources được cleanup properly bằng cách:
1. Create/destroy RagEngine nhiều lần
2. Monitor memory usage
3. Verify memory không tăng liên tục (no leaks)
"""

import gc
import os
import shutil
import tempfile
import time
from pathlib import Path

import psutil


def get_memory_mb():
    """Get current process memory in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def test_rag_engine_no_memory_leak():
    """
    Test RagEngine không có memory leaks.

    ✅ Test strategy:
    1. Tạo temporary persist directory
    2. Create và destroy RagEngine 10 lần
    3. Force garbage collection sau mỗi iteration
    4. Verify memory không tăng > 50MB (reasonable threshold)
    """
    print("🧪 Testing RagEngine for memory leaks...\n")

    # Import here để tránh side effects
    from app.rag_engine import RagEngine

    # Tạo temp directory
    temp_dir = tempfile.mkdtemp(prefix="ollama_rag_test_")
    print(f"📁 Temp directory: {temp_dir}")

    try:
        # Baseline memory
        gc.collect()
        time.sleep(0.5)
        baseline_memory = get_memory_mb()
        print(f"📊 Baseline memory: {baseline_memory:.2f} MB\n")

        memories = []

        # Create and destroy engine multiple times
        for i in range(10):
            print(f"Iteration {i + 1}/10...")

            # Create engine
            engine = RagEngine(persist_dir=temp_dir)

            # Do some operations
            engine.list_dbs()
            engine.get_filters()

            # Cleanup explicitly
            engine.cleanup()
            del engine

            # Force garbage collection
            gc.collect()
            time.sleep(0.2)

            # Measure memory
            current_memory = get_memory_mb()
            delta = current_memory - baseline_memory
            memories.append(current_memory)
            print(f"  Memory: {current_memory:.2f} MB (Δ {delta:+.2f} MB)")

        print()

        # Analyze results
        final_memory = memories[-1]
        max_memory = max(memories)
        memory_growth = final_memory - baseline_memory

        print("=" * 60)
        print("📈 MEMORY ANALYSIS")
        print("=" * 60)
        print(f"Baseline:       {baseline_memory:.2f} MB")
        print(f"Final:          {final_memory:.2f} MB")
        print(f"Peak:           {max_memory:.2f} MB")
        print(f"Growth:         {memory_growth:+.2f} MB")
        print("=" * 60)

        # Verdict
        THRESHOLD_MB = 50.0  # 50MB threshold for memory growth
        if memory_growth < THRESHOLD_MB:
            print(f"✅ PASS: Memory growth ({memory_growth:.2f} MB) < threshold ({THRESHOLD_MB} MB)")
            print("🎉 No significant memory leaks detected!")
            return True
        else:
            print(
                f"⚠️  WARNING: Memory growth ({memory_growth:.2f} MB) >= threshold ({THRESHOLD_MB} MB)"
            )
            print("   This might indicate a memory leak.")
            return False

    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"\n🧹 Cleaned up: {temp_dir}")
        except Exception as e:
            print(f"\n⚠️  Failed to cleanup {temp_dir}: {e}")


def test_file_handles_cleanup():
    """
    Test file handles được cleanup properly.

    ✅ Verify:
    - ChatStore operations không leak file handles
    - FeedbackStore operations không leak file handles
    """
    print("\n" + "=" * 60)
    print("🧪 Testing file handles cleanup...\n")

    from app.chat_store import ChatStore
    from app.feedback_store import FeedbackStore

    # Tạo temp directory
    temp_dir = tempfile.mkdtemp(prefix="ollama_rag_handles_")
    print(f"📁 Temp directory: {temp_dir}")

    try:
        process = psutil.Process()

        # Baseline open files
        baseline_files = process.num_fds() if hasattr(process, "num_fds") else 0
        print(f"📊 Baseline open file descriptors: {baseline_files}\n")

        # Test ChatStore
        chat_store = ChatStore(temp_dir)
        for i in range(20):
            chat = chat_store.create("test_db", f"Chat {i}")
            chat_store.append_pair(
                "test_db", chat["id"], f"Question {i}", f"Answer {i}"
            )
            chat_store.get("test_db", chat["id"])

        # Test FeedbackStore
        feedback_store = FeedbackStore(temp_dir)
        for i in range(20):
            feedback_store.append("test_db", {"rating": 5, "comment": f"Test {i}"})

        feedback_store.list("test_db")

        # Force cleanup
        del chat_store
        del feedback_store
        gc.collect()
        time.sleep(0.5)

        # Check open files
        if hasattr(process, "num_fds"):
            final_files = process.num_fds()
            file_growth = final_files - baseline_files
            print(f"📊 Final open file descriptors: {final_files}")
            print(f"📈 File descriptor growth: {file_growth:+d}")

            if file_growth <= 5:  # Allow small growth (system files, etc.)
                print("✅ PASS: No file handle leaks detected!")
                return True
            else:
                print(
                    f"⚠️  WARNING: File descriptor growth ({file_growth}) might indicate leak"
                )
                return False
        else:
            print("ℹ️  File descriptor counting not available on this platform")
            print("✅ Test completed (no verification)")
            return True

    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"\n🧹 Cleaned up: {temp_dir}")
        except Exception as e:
            print(f"\n⚠️  Failed to cleanup {temp_dir}: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🔬 MEMORY LEAK DETECTION TEST SUITE")
    print("=" * 60)
    print()

    # Run tests
    test1_pass = test_rag_engine_no_memory_leak()
    test2_pass = test_file_handles_cleanup()

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"RagEngine memory test:    {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"File handles test:        {'✅ PASS' if test2_pass else '❌ FAIL'}")
    print("=" * 60)

    if test1_pass and test2_pass:
        print("🎉 ALL TESTS PASSED - No memory leaks detected!")
        exit(0)
    else:
        print("⚠️  SOME TESTS FAILED - Review memory management")
        exit(1)
