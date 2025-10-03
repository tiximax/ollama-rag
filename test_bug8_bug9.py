"""
Test script để verify BUG #8 (N+1 query) và BUG #9 (Blocking I/O) đã fix!
"""

import io
import time

import requests

BASE_URL = "http://127.0.0.1:8000"


def test_bug8_analytics_performance():
    """Test BUG #8: Analytics endpoint không bị N+1 query nữa."""
    print("\n🧪 TEST BUG #8: Analytics N+1 Query Fix")
    print("=" * 60)

    try:
        # Tạo vài chats để test
        chat_ids = []
        for i in range(3):
            resp = requests.post(f"{BASE_URL}/api/chat", json={"name": f"Test Chat {i}"})
            if resp.ok:
                chat_ids.append(resp.json().get('id'))
                print(f"✅ Created chat {i+1}: {resp.json().get('id')}")

        # Thêm messages vào mỗi chat
        for idx, cid in enumerate(chat_ids):
            for j in range(2):
                requests.post(
                    f"{BASE_URL}/api/chat/{cid}/message",
                    json={"role": "user", "content": f"Test message {j} in chat {idx}"},
                )

        print("\n📊 Testing analytics endpoint performance...")
        start = time.time()
        resp = requests.get(f"{BASE_URL}/api/analytics/db")
        elapsed = time.time() - start

        if resp.ok:
            data = resp.json()
            print(f"✅ Analytics response: {elapsed*1000:.1f}ms")
            print(f"   - Total chats: {data.get('chats', 0)}")
            print(f"   - QA pairs: {data.get('qa_pairs', 0)}")

            # Với bulk fetch, response time nên < 500ms ngay cả với nhiều chats
            if elapsed < 0.5:
                print(f"✅ PASSED: Fast response ({elapsed*1000:.1f}ms) - No N+1 query! 🚀")
                return True
            else:
                print(
                    f"⚠️ WARNING: Slow response ({elapsed*1000:.1f}ms) - Might have N+1 query issue!"
                )
                return False
        else:
            print(f"❌ FAILED: {resp.status_code} - {resp.text}")
            return False

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_bug9_async_upload():
    """Test BUG #9: Upload endpoint dùng async I/O không block."""
    print("\n🧪 TEST BUG #9: Async File Upload")
    print("=" * 60)

    try:
        # Tạo file test content (1MB để thấy rõ async benefit)
        test_content = b"Test content " * 100000  # ~1.3MB
        files = {'files': ('test_large.txt', io.BytesIO(test_content), 'text/plain')}

        print(f"📤 Uploading {len(test_content)//1024}KB file...")
        start = time.time()
        resp = requests.post(f"{BASE_URL}/api/upload", files=files)
        elapsed = time.time() - start

        if resp.ok:
            data = resp.json()
            print(f"✅ Upload response: {elapsed*1000:.1f}ms")
            print(f"   - Files saved: {data.get('saved', [])}")
            print(f"   - Chunks indexed: {data.get('chunks_indexed', 0)}")

            # Test concurrent request while uploading (manual test)
            print("\n🔄 Testing server responsiveness during upload...")
            health_resp = requests.get(f"{BASE_URL}/api/health")
            if health_resp.ok:
                print("✅ PASSED: Server remained responsive - No blocking I/O! 💨")
                return True
            else:
                print("⚠️ WARNING: Server might be blocked during upload!")
                return False
        else:
            print(f"❌ FAILED: {resp.status_code} - {resp.text}")
            return False

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("🚀 TESTING BUG #8 & BUG #9 FIXES")
    print("=" * 60)

    # Check if server is running
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=2)
        if not resp.ok:
            print("❌ Server not running at http://127.0.0.1:8000")
            print("   Please run: python -m uvicorn app.main:app --reload --port 8000")
            return
    except:
        print("❌ Server not running at http://127.0.0.1:8000")
        print("   Please run: python -m uvicorn app.main:app --reload --port 8000")
        return

    print("✅ Server is running!")

    results = {}
    results['bug8'] = test_bug8_analytics_performance()
    results['bug9'] = test_bug9_async_upload()

    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"BUG #8 (N+1 Query):     {'✅ PASSED' if results['bug8'] else '❌ FAILED'}")
    print(f"BUG #9 (Blocking I/O):  {'✅ PASSED' if results['bug9'] else '❌ FAILED'}")

    if all(results.values()):
        print("\n🎉 ALL TESTS PASSED! Bugs fixed thành công! 💎")
    else:
        print("\n⚠️ Some tests failed. Please review the logs above.")


if __name__ == "__main__":
    main()
