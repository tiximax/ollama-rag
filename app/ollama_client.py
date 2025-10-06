import json
import logging
import os
import time
from collections.abc import Iterator

import requests
from dotenv import load_dotenv

from app.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError

load_dotenv()

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# Configurable networking behavior
CONNECT_TIMEOUT = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "5"))
READ_TIMEOUT = float(os.getenv("OLLAMA_READ_TIMEOUT", "180"))
MAX_RETRIES = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))
BACKOFF_FACTOR = float(os.getenv("OLLAMA_RETRY_BACKOFF", "0.6"))
# Optional tuning for performance/CPU usage
OPT_NUM_CTX = os.getenv("OLLAMA_NUM_CTX")
OPT_NUM_THREAD = os.getenv("OLLAMA_NUM_THREAD")
OPT_NUM_GPU = os.getenv("OLLAMA_NUM_GPU")


class OllamaClient:
    def __init__(self, base_url: str | None = None, enable_circuit_breaker: bool = True):
        """
        Initialize Ollama client với Circuit Breaker protection! 🛡️

        Args:
            base_url: Ollama service URL
            enable_circuit_breaker: Enable circuit breaker for resilience (default: True)
        """
        self.base_url = base_url or OLLAMA_BASE_URL
        self.session = requests.Session()

        # Circuit Breaker configuration - ổn định như kim cương! 💎
        if enable_circuit_breaker:
            circuit_config = CircuitBreakerConfig(
                failure_threshold=5,  # Open after 5 consecutive failures
                timeout=30.0,  # Try recovery after 30s
                success_threshold=2,  # Close after 2 successful calls
                window_size=10,
                half_open_max_calls=3,
            )
            self._circuit_breaker = CircuitBreaker(
                name="ollama_client",
                config=circuit_config,
                on_state_change=self._on_circuit_state_change,
            )
            logger.info("🔌 Circuit Breaker enabled for Ollama client")
        else:
            self._circuit_breaker = None
            logger.info("⚠️ Circuit Breaker disabled for Ollama client")

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body=None,
        stream: bool = False,
        timeout: tuple[float, float] | None = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None
        to = timeout or (CONNECT_TIMEOUT, READ_TIMEOUT)
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self.session.request(
                    method,
                    url,
                    json=json_body,
                    stream=stream,
                    timeout=to,
                    headers={"Connection": "close"},
                )
                # Retry on common transient status codes
                if resp.status_code in (429, 502, 503, 504) or 500 <= resp.status_code < 600:
                    last_exc = requests.HTTPError(
                        f"{resp.status_code}: transient error", response=resp
                    )
                    # Drain/close response before retry
                    try:
                        resp.close()
                    except Exception:
                        pass
                    raise last_exc
                return resp
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
                last_exc = e
                if attempt >= MAX_RETRIES:
                    break
                time.sleep(BACKOFF_FACTOR * (2**attempt))
            except Exception as e:
                # Don't retry on unknown fatal errors
                last_exc = e
                break
        if last_exc:
            raise last_exc
        raise RuntimeError("Request failed without exception")

    def _on_circuit_state_change(self, old_state, new_state):
        """Callback when circuit breaker state changes - logging như pro! 📢"""
        logger.warning(
            f"🔄 Ollama Circuit Breaker state changed: {old_state.value} → {new_state.value}"
        )

    def get_circuit_metrics(self) -> dict:
        """Get circuit breaker metrics - for monitoring! 📊"""
        if self._circuit_breaker:
            return self._circuit_breaker.get_metrics()
        return {"circuit_breaker": "disabled"}

    def health_check(self) -> bool:
        """Check if Ollama service is healthy."""
        try:
            response = self.session.post(f"{self.base_url}/api/tags", timeout=CONNECT_TIMEOUT)
            return response.status_code == 200
        except Exception:
            return False

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings với Circuit Breaker protection! 🛡️"""
        if self._circuit_breaker:
            try:
                return self._circuit_breaker.call(self._embed_impl, texts)
            except CircuitBreakerError as e:
                logger.error(
                    f"🚨 Circuit breaker OPEN for embed: {e}. "
                    f"Consecutive failures: {e.stats.consecutive_failures if e.stats else 'N/A'}"
                )
                # Fallback: Return empty embeddings để không crash toàn bộ
                logger.warning(f"⚠️ Returning empty embeddings as fallback for {len(texts)} texts")
                return [[0.0] * 768 for _ in texts]  # Default embedding dimension
        else:
            return self._embed_impl(texts)

    def _embed_impl(self, texts: list[str]) -> list[list[float]]:
        """Internal implementation of embed - wrapped by circuit breaker."""
        embeddings: list[list[float]] = []
        for t in texts:
            resp = self._request(
                "POST",
                "/api/embeddings",
                json_body={"model": EMBED_MODEL, "prompt": t},
                stream=False,
            )
            resp.raise_for_status()
            data = resp.json()
            emb = data.get("embedding")
            if not emb:
                raise RuntimeError(f"Ollama embedding failed: {data}")
            embeddings.append(emb)
        return embeddings

    def _gen_options(self) -> dict:
        opts: dict = {}
        try:
            if OPT_NUM_CTX is not None:
                opts["num_ctx"] = int(OPT_NUM_CTX)
            if OPT_NUM_THREAD is not None:
                opts["num_thread"] = int(OPT_NUM_THREAD)
            if OPT_NUM_GPU is not None:
                # 0=CPU only
                opts["num_gpu"] = int(OPT_NUM_GPU)
        except Exception:
            pass
        return opts

    def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate text với Circuit Breaker protection! 🛡️"""
        if self._circuit_breaker:
            try:
                return self._circuit_breaker.call(self._generate_impl, prompt, system)
            except CircuitBreakerError as e:
                logger.error(
                    f"🚨 Circuit breaker OPEN for generate: {e}. "
                    f"Consecutive failures: {e.stats.consecutive_failures if e.stats else 'N/A'}"
                )
                # Fallback: Return helpful error message
                return (
                    "[Service temporarily unavailable. The AI service is experiencing issues. "
                    "Please try again in a moment.]"
                )
        else:
            return self._generate_impl(prompt, system)

    def _generate_impl(self, prompt: str, system: str | None = None) -> str:
        """Internal implementation of generate - wrapped by circuit breaker."""
        payload = {
            "model": LLM_MODEL,
            "prompt": prompt if system is None else f"[SYSTEM]\n{system}\n[/SYSTEM]\n{prompt}",
            "stream": False,
            "options": self._gen_options(),
        }
        resp = self._request("POST", "/api/generate", json_body=payload, stream=False)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")

    def generate_stream(self, prompt: str, system: str | None = None) -> Iterator[str]:
        payload = {
            "model": LLM_MODEL,
            "prompt": prompt if system is None else f"[SYSTEM]\n{system}\n[/SYSTEM]\n{prompt}",
            "stream": True,
            "options": self._gen_options(),
        }
        resp = self._request("POST", "/api/generate", json_body=payload, stream=True)
        with resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                if "response" in data and data["response"]:
                    yield data["response"]
                if data.get("done"):
                    break
