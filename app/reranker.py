import os
from typing import List, Dict, Any, Tuple, Optional

# Optional deps
try:
    import onnxruntime as ort  # type: ignore
except Exception:  # pragma: no cover
    ort = None  # type: ignore

try:
    from transformers import AutoTokenizer  # type: ignore
except Exception:  # pragma: no cover
    AutoTokenizer = None  # type: ignore

try:
    from huggingface_hub import hf_hub_download  # type: ignore
except Exception:  # pragma: no cover
    hf_hub_download = None  # type: ignore

import numpy as np  # type: ignore


class BgeOnnxReranker:
    """
    Reranker dùng ONNXRuntime cho model BAAI/bge-reranker-v2-m3 (nếu có ONNX).
    Nếu không khả dụng, phương thức available() sẽ trả về False.
    """

    def __init__(self, repo_id: str = "BAAI/bge-reranker-v2-m3", onnx_filename: str = "onnx/model.onnx", max_length: int = 512):
        self.repo_id = repo_id
        self.onnx_filename = onnx_filename
        self.max_length = max_length
        self._session: Optional["ort.InferenceSession"] = None
        self._tokenizer = None
        self._input_names: List[str] = []
        self._output_names: List[str] = []
        self._init_try()

    def available(self) -> bool:
        return self._session is not None and self._tokenizer is not None

    def _init_try(self) -> None:
        if ort is None or AutoTokenizer is None or hf_hub_download is None:
            return
        try:
            model_path = hf_hub_download(repo_id=self.repo_id, filename=self.onnx_filename)
        except Exception:
            # thử đường dẫn fallback (nếu repo không có thư mục onnx)
            try:
                model_path = hf_hub_download(repo_id=self.repo_id, filename="model.onnx")
            except Exception:
                return
        try:
            sess_options = ort.SessionOptions()
            self._session = ort.InferenceSession(model_path, sess_options=sess_options, providers=["CPUExecutionProvider"])  # type: ignore[arg-type]
            self._input_names = [i.name for i in self._session.get_inputs()]
            self._output_names = [o.name for o in self._session.get_outputs()]
            self._tokenizer = AutoTokenizer.from_pretrained(self.repo_id, use_fast=True)
        except Exception:
            self._session = None
            self._tokenizer = None
            self._input_names = []
            self._output_names = []

    def score(self, query: str, docs: List[str], batch_size: int = 16) -> List[float]:
        if not self.available():
            raise RuntimeError("BGE ONNX reranker not available")
        assert self._session is not None and self._tokenizer is not None
        scores: List[float] = []
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i+batch_size]
            enc = self._tokenizer(
                [query] * len(batch),
                batch,
                truncation=True,
                padding=True,
                max_length=self.max_length,
                return_tensors='np'
            )
            inputs: Dict[str, np.ndarray] = {}
            for name in self._input_names:
                if name in enc:
                    arr = enc[name]
                elif name == 'token_type_ids' and 'token_type_ids' not in enc:
                    # nếu không có token_type_ids (robust cho tokenizer không dùng segment ids)
                    shape = enc['input_ids'].shape
                    arr = np.zeros(shape, dtype=np.int64)
                else:
                    continue
                # đảm bảo dtype int64 cho ids/masks
                if arr.dtype != np.int64:
                    try:
                        arr = arr.astype(np.int64)
                    except Exception:
                        pass
                inputs[name] = arr
            out = self._session.run(self._output_names, inputs)
            logits = out[0]  # (batch, 1) or (batch, num_labels)
            logits = np.array(logits).reshape(-1)
            scores.extend(logits.tolist())
        return scores

    def rerank(self, query: str, docs: List[str], metas: List[Dict[str, Any]], top_k: int) -> Tuple[List[str], List[Dict[str, Any]]]:
        scores = self.score(query, docs)
        idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [docs[i] for i in idxs], [metas[i] for i in idxs]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    na = np.linalg.norm(va) + 1e-12
    nb = np.linalg.norm(vb) + 1e-12
    return float(np.dot(va, vb) / (na * nb))


class SimpleEmbedReranker:
    """Reranker fallback: dùng embedding cosine similarity (Ollama embed)."""

    def __init__(self, embedder):
        self.embedder = embedder  # callable: List[str] -> List[List[float]]

    def rerank(self, query: str, docs: List[str], metas: List[Dict[str, Any]], top_k: int) -> Tuple[List[str], List[Dict[str, Any]]]:
        embs = self.embedder([query] + docs)
        q_emb = embs[0]
        d_embs = embs[1:]
        pairs = [
            (cosine_similarity(q_emb, d_embs[i]), i)
            for i in range(len(docs))
        ]
        pairs.sort(key=lambda x: x[0], reverse=True)
        idxs = [i for _, i in pairs[:top_k]]
        return [docs[i] for i in idxs], [metas[i] for i in idxs]
