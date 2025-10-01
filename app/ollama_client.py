import os
import requests
import json
import time
from typing import List, Optional, Iterator, Tuple

from dotenv import load_dotenv

load_dotenv()

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
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.session = requests.Session()

    def _request(self, method: str, path: str, *, json_body=None, stream: bool = False, timeout: Optional[Tuple[float, float]] = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        to = timeout or (CONNECT_TIMEOUT, READ_TIMEOUT)
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self.session.request(method, url, json=json_body, stream=stream, timeout=to, headers={"Connection": "close"})
                # Retry on common transient status codes
                if resp.status_code in (429, 502, 503, 504) or 500 <= resp.status_code < 600:
                    last_exc = requests.HTTPError(f"{resp.status_code}: transient error", response=resp)
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
                time.sleep(BACKOFF_FACTOR * (2 ** attempt))
            except Exception as e:
                # Don't retry on unknown fatal errors
                last_exc = e
                break
        if last_exc:
            raise last_exc
        raise RuntimeError("Request failed without exception")

    def health_check(self) -> bool:
        """Check if Ollama service is healthy."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/tags",
                timeout=CONNECT_TIMEOUT
            )
            return response.status_code == 200
        except Exception:
            return False

    def embed(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
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

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
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

    def generate_stream(self, prompt: str, system: Optional[str] = None) -> Iterator[str]:
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
