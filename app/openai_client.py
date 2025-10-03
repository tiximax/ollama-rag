import json
import os
import time
from collections.abc import Iterator

import requests

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CONNECT_TIMEOUT = float(os.getenv("OPENAI_CONNECT_TIMEOUT", "5"))
READ_TIMEOUT = float(os.getenv("OPENAI_READ_TIMEOUT", "180"))
MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
BACKOFF_FACTOR = float(os.getenv("OPENAI_RETRY_BACKOFF", "0.6"))


class OpenAIClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or OPENAI_BASE_URL
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.session = requests.Session()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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
                    method, url, json=json_body, stream=stream, timeout=to, headers=self._headers()
                )
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_exc = requests.HTTPError(f"{resp.status_code}: transient", response=resp)
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
                last_exc = e
                break
        if last_exc:
            raise last_exc
        raise RuntimeError("OpenAI request failed")

    def generate(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": OPENAI_MODEL,
            "messages": messages,
            "stream": False,
        }
        resp = self._request("POST", "/chat/completions", json_body=payload, stream=False)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return ""

    def generate_stream(self, prompt: str, system: str | None = None) -> Iterator[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": OPENAI_MODEL,
            "messages": messages,
            "stream": True,
        }
        resp = self._request("POST", "/chat/completions", json_body=payload, stream=True)
        with resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    chunk = line[len("data: ") :].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                        delta = data["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue
