import os
import uuid
import re
import shutil
import json
import logging
from typing import List, Dict, Any, Sequence, Optional, Tuple

from dotenv import load_dotenv

from chromadb import PersistentClient
from chromadb.api.types import Documents, Embeddings, IDs, Metadatas
from chromadb.config import Settings

from .ollama_client import OllamaClient
from .openai_client import OpenAIClient  # type: ignore
from .reranker import BgeOnnxReranker, SimpleEmbedReranker

try:
    from rank_bm25 import BM25Okapi  # type: ignore
except Exception:  # pragma: no cover
    BM25Okapi = None  # fallback if package not installed

load_dotenv()
# Giảm nhiễu log/telemetry từ chromadb trong test/CI
for _name in ("chromadb", "chromadb.telemetry", "chromadb.telemetry.posthog"):
    try:
        logging.getLogger(_name).setLevel(logging.CRITICAL)
    except Exception:
        pass

DEFAULT_PERSIST = os.getenv("PERSIST_DIR")
PERSIST_ROOT = os.getenv("PERSIST_ROOT", "data/kb")
DEFAULT_DB = os.getenv("DB_NAME", "default")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

# RRF config
RRF_ENABLE_DEFAULT = os.getenv("RRF_ENABLE", "1").strip() not in ("0", "false", "False")
RRF_K_DEFAULT = int(os.getenv("RRF_K", "60"))


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = text.replace("\r\n", "\n")
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == n:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


def extract_text_from_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        texts: List[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t:
                texts.append(t)
        return "\n\n".join(texts)
    except Exception:
        return ""


def extract_text_from_docx(path: str) -> str:
    try:
        from docx import Document
        doc = Document(path)
        paras = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(paras)
    except Exception:
        return ""


class OllamaEmbeddingFunction:
    """Embedding function wrapper để dùng với ChromaDB."""

    def __init__(self, client: OllamaClient):
        self.client = client

    def __call__(self, input: Sequence[str]) -> Embeddings:
        return self.client.embed(list(input))


class RagEngine:
    def __init__(self, persist_dir: Optional[str] = DEFAULT_PERSIST, collection_name: str = "docs", persist_root: Optional[str] = None, db_name: Optional[str] = None):
        # Determine persist_root and db_name
        if persist_dir:
            root = os.path.dirname(persist_dir)
            base = os.path.basename(persist_dir)
            self.persist_root = root if root else (persist_root or PERSIST_ROOT)
            self.db_name = base if base else (db_name or DEFAULT_DB)
        else:
            self.persist_root = persist_root or PERSIST_ROOT
            self.db_name = db_name or DEFAULT_DB
        self.collection_name = collection_name

        self.ollama = OllamaClient()
        self._openai: Optional[OpenAIClient] = None
        self.default_provider = os.getenv("PROVIDER", "ollama").lower()
        # Initialize storage and client
        self._init_client()

        # BM25 state (in-memory)
        self._bm25 = None  # type: ignore
        self._bm25_docs: List[str] = []
        self._bm25_metas: List[Dict[str, Any]] = []
        self._bm25_tokens: List[List[str]] = []
        # Reranker
        self._bge_rr: Optional[BgeOnnxReranker] = None
        self._embed_rr: Optional[SimpleEmbedReranker] = None

    # ===== Multi-DB =====
    @property
    def persist_dir(self) -> str:
        return os.path.join(self.persist_root, self.db_name)

    def _init_client(self) -> None:
        os.makedirs(self.persist_dir, exist_ok=True)
        try:
            self.client = PersistentClient(path=self.persist_dir, settings=Settings(anonymized_telemetry=False))
        except Exception:
            # Fallback nếu phiên bản chromadb không hỗ trợ Settings
            self.client = PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=OllamaEmbeddingFunction(self.ollama),
        )
        # invalidate bm25 on (re)init
        self._bm25 = None

    def list_dbs(self) -> List[str]:
        if not os.path.isdir(self.persist_root):
            return []
        names = []
        for entry in os.listdir(self.persist_root):
            p = os.path.join(self.persist_root, entry)
            if os.path.isdir(p):
                names.append(entry)
        names.sort()
        return names

    @staticmethod
    def _valid_db_name(name: str) -> bool:
        """Allow only safe names to avoid path traversal or invalid folders.
        Accept [A-Za-z0-9_.-], length 1..64.
        """
        if not isinstance(name, str):
            return False
        if not (1 <= len(name) <= 64):
            return False
        return re.fullmatch(r"[A-Za-z0-9_.-]+", name) is not None

    def use_db(self, name: str) -> str:
        if not self._valid_db_name(name):
            raise ValueError("Invalid db name")
        if name == self.db_name:
            return self.db_name
        self.db_name = name
        self._init_client()
        return self.db_name

    def create_db(self, name: str) -> str:
        if not self._valid_db_name(name):
            raise ValueError("Invalid db name")
        p = os.path.join(self.persist_root, name)
        if os.path.exists(p):
            raise FileExistsError(f"DB '{name}' already exists")
        os.makedirs(p, exist_ok=False)
        return name

    def delete_db(self, name: str) -> None:
        if not self._valid_db_name(name):
            raise ValueError("Invalid db name")
        p = os.path.join(self.persist_root, name)
        if not os.path.exists(p):
            return
        # If deleting current DB, switch to DEFAULT_DB (create if needed)
        deleting_current = (name == self.db_name)
        shutil.rmtree(p, ignore_errors=True)
        if deleting_current:
            self.db_name = DEFAULT_DB
            self._init_client()

    # ===== Ingest =====
    def ingest_texts(self, texts: List[str], metadatas: List[Dict[str, Any]] | None = None) -> int:
        ids: IDs = []
        docs: Documents = []
        mds: Metadatas = []

        for i, t in enumerate(texts):
            for j, chunk in enumerate(chunk_text(t)):
                ids.append(str(uuid.uuid4()))
                docs.append(chunk)
                meta = {"source": metadatas[i].get("source") if metadatas else f"text_{i}", "chunk": j}
                mds.append(meta)
        self.collection.add(ids=ids, documents=docs, metadatas=mds)
        # invalidate bm25 to rebuild on next query
        self._bm25 = None
        return len(docs)

    def ingest_paths(self, paths: List[str]) -> int:
        import glob

        contents: List[str] = []
        metas: List[Dict[str, Any]] = []
        for p in paths:
            for file in glob.glob(p, recursive=True):
                if os.path.isdir(file):
                    # Ingest *.txt, *.pdf, *.docx recursively
                    for pattern in ("*.txt", "*.pdf", "*.docx"):
                        for f2 in glob.glob(os.path.join(file, "**", pattern), recursive=True):
                            text = ""
                            try:
                                if f2.lower().endswith(".txt"):
                                    with open(f2, "r", encoding="utf-8") as fh:
                                        text = fh.read()
                                elif f2.lower().endswith(".pdf"):
                                    text = extract_text_from_pdf(f2)
                                elif f2.lower().endswith(".docx"):
                                    text = extract_text_from_docx(f2)
                            except Exception:
                                text = ""
                            if text:
                                contents.append(text)
                                metas.append({"source": f2})
                else:
                    text = ""
                    try:
                        if file.lower().endswith(".txt"):
                            with open(file, "r", encoding="utf-8") as fh:
                                text = fh.read()
                        elif file.lower().endswith(".pdf"):
                            text = extract_text_from_pdf(file)
                        elif file.lower().endswith(".docx"):
                            text = extract_text_from_docx(file)
                    except Exception:
                        text = ""
                    if text:
                        contents.append(text)
                        metas.append({"source": file})
        if not contents:
            return 0
        return self.ingest_texts(contents, metas)

    # ===== Tokenize & BM25 =====
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", (text or "").lower())

    def _build_bm25_from_collection(self) -> None:
        if BM25Okapi is None:
            self._bm25 = None
            self._bm25_docs = []
            self._bm25_metas = []
            self._bm25_tokens = []
            return
        try:
            # Try new API with include
            results = self.collection.get(include=["documents", "metadatas"])  # type: ignore[arg-type]
            docs: List[str] = results.get("documents", [])  # type: ignore[assignment]
            metas: List[Dict[str, Any]] = results.get("metadatas", [])  # type: ignore[assignment]
        except Exception:
            # Fallback without include
            results = self.collection.get()
            docs = results.get("documents", [])  # type: ignore[assignment]
            metas = results.get("metadatas", [])  # type: ignore[assignment]
        # Filter empties keeping alignment
        new_docs: List[str] = []
        new_metas: List[Dict[str, Any]] = []
        new_tokens: List[List[str]] = []
        for d, m in zip(docs, metas):
            if d and d.strip():
                new_docs.append(d)
                new_metas.append(m)
                new_tokens.append(self._tokenize(d))
        if not new_docs:
            self._bm25 = None
            self._bm25_docs = []
            self._bm25_metas = []
            self._bm25_tokens = []
            return
        self._bm25 = BM25Okapi(new_tokens)  # type: ignore[operator]
        self._bm25_docs = new_docs
        self._bm25_metas = new_metas
        self._bm25_tokens = new_tokens

    def _ensure_bm25(self) -> bool:
        if self._bm25 is None:
            self._build_bm25_from_collection()
        return self._bm25 is not None

    # ===== Retrieval =====
    def retrieve(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        results = self.collection.query(query_texts=[query], n_results=top_k)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0] if "ids" in results else []
        return {"documents": docs, "metadatas": metas, "distances": dists, "ids": ids}

    def retrieve_bm25(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        if not self._ensure_bm25():
            return {"documents": [], "metadatas": [], "scores": []}
        q_tokens = self._tokenize(query)
        scores_list = list(self._bm25.get_scores(q_tokens))  # type: ignore[union-attr]
        # top indices by score desc
        idxs = sorted(range(len(scores_list)), key=lambda i: scores_list[i], reverse=True)[:top_k]
        docs = [self._bm25_docs[i] for i in idxs]
        metas = [self._bm25_metas[i] for i in idxs]
        scores = [scores_list[i] for i in idxs]
        return {"documents": docs, "metadatas": metas, "scores": scores}

    @staticmethod
    def _to_similarity(distances: List[float]) -> List[float]:
        # Convert distance to similarity in [0,1) using 1/(1+d)
        sims = [1.0 / (1.0 + float(d)) for d in distances]
        return sims

    @staticmethod
    def _min_max(values: List[float]) -> List[float]:
        if not values:
            return []
        vmin = min(values)
        vmax = max(values)
        if vmax - vmin <= 1e-12:
            return [1.0 for _ in values]
        return [(v - vmin) / (vmax - vmin) for v in values]

    @staticmethod
    def _make_key(doc: str, meta: Dict[str, Any]) -> Tuple[str, Any, Any]:
        return (meta.get("source", ""), meta.get("chunk", -1), len(doc))

    def retrieve_hybrid(self, query: str, top_k: int = 5, bm25_weight: float = 0.5, rrf_enable: Optional[bool] = None, rrf_k: Optional[int] = None) -> Dict[str, Any]:
        # Fetch candidates
        vec = self.retrieve(query, top_k=top_k)
        bm = self.retrieve_bm25(query, top_k=max(top_k, 10))  # get a bit more for better merge

        v_docs: List[str] = vec.get("documents", [])
        v_metas: List[Dict[str, Any]] = vec.get("metadatas", [])
        v_dists: List[float] = vec.get("distances", [])
        v_sims = self._to_similarity(v_dists)
        v_norm = self._min_max(v_sims)

        b_docs: List[str] = bm.get("documents", [])
        b_metas: List[Dict[str, Any]] = bm.get("metadatas", [])
        b_scores: List[float] = bm.get("scores", [])
        b_norm = self._min_max(b_scores)

        # Decide fusion strategy
        use_rrf = RRF_ENABLE_DEFAULT if rrf_enable is None else bool(rrf_enable)
        rrf_k_val = RRF_K_DEFAULT if rrf_k is None else int(rrf_k)

        if use_rrf:
            # Build ranks
            ranks_vec: Dict[Tuple[str, Any, Any], int] = {}
            for idx, (doc, meta) in enumerate(zip(v_docs, v_metas), start=1):
                ranks_vec[self._make_key(doc, meta)] = idx
            ranks_bm: Dict[Tuple[str, Any, Any], int] = {}
            for idx, (doc, meta) in enumerate(zip(b_docs, b_metas), start=1):
                ranks_bm[self._make_key(doc, meta)] = idx
            # Union keys
            keys = set(ranks_vec.keys()) | set(ranks_bm.keys())
            combined = []
            for key in keys:
                r1 = ranks_vec.get(key)
                r2 = ranks_bm.get(key)
                score = 0.0
                if r1 is not None:
                    score += 1.0 / (rrf_k_val + r1)
                if r2 is not None:
                    score += 1.0 / (rrf_k_val + r2)
                # pick representative doc/meta (prefer vector side if available)
                if key in ranks_vec:
                    i = r1 - 1  # type: ignore
                    doc = v_docs[i]
                    meta = v_metas[i]
                else:
                    i = r2 - 1  # type: ignore
                    doc = b_docs[i]
                    meta = b_metas[i]
                combined.append((score, doc, meta))
            combined.sort(key=lambda x: x[0], reverse=True)
            docs = [d for _, d, _ in combined[:top_k]]
            metas = [m for _, _, m in combined[:top_k]]
            return {"documents": docs, "metadatas": metas}
        else:
            # Weighted normalization merge (legacy)
            cand: Dict[Tuple[str, Any, Any], Dict[str, Any]] = {}
            for doc, meta, s in zip(v_docs, v_metas, v_norm):
                key = self._make_key(doc, meta)
                cand[key] = {"doc": doc, "meta": meta, "v": s, "b": 0.0}
            for doc, meta, s in zip(b_docs, b_metas, b_norm):
                key = self._make_key(doc, meta)
                if key in cand:
                    cand[key]["b"] = s
                else:
                    cand[key] = {"doc": doc, "meta": meta, "v": 0.0, "b": s}
            combined = []
            w = max(0.0, min(1.0, float(bm25_weight)))
            for item in cand.values():
                score = (1.0 - w) * item["v"] + w * item["b"]
                combined.append((score, item["doc"], item["meta"]))
            combined.sort(key=lambda x: x[0], reverse=True)
            docs = [d for _, d, _ in combined[:top_k]]
            metas = [m for _, _, m in combined[:top_k]]
            return {"documents": docs, "metadatas": metas}

    # ===== Prompt & Answer =====
    def build_prompt(self, question: str, context_docs: List[str]) -> str:
        context_block = "\n\n".join([f"[CTX {i+1}]\n{c}" for i, c in enumerate(context_docs)])
        # Hướng dẫn rõ ràng về citations [n] khớp với [CTX n]
        system = (
            "Bạn là trợ lý AI tiếng Việt, trả lời ngắn gọn, chính xác và chỉ dựa trên phần 'Ngữ cảnh' được cung cấp. "
            "Khi sử dụng thông tin từ một CTX, hãy chèn citation dạng [n] với n là số thứ tự CTX tương ứng (ví dụ [1], [2]). "
            "Có thể chèn nhiều [n] nếu nhiều nguồn liên quan. Không tạo citation nếu không có căn cứ trong ngữ cảnh. "
            "Nếu không đủ thông tin để trả lời, hãy nói bạn không chắc thay vì suy đoán."
        )
        prompt = (
            f"{system}\n\n"
            f"Ngữ cảnh:\n{context_block}\n\n"
            f"Câu hỏi: {question}\n\n"
            f"Trả lời (tiếng Việt), nhớ chèn [n] khi trích dẫn CTX phù hợp:"
        )
        return prompt

    def _ensure_rerankers(self) -> None:
        if self._bge_rr is None:
            try:
                self._bge_rr = BgeOnnxReranker()
            except Exception:
                self._bge_rr = None
        if self._embed_rr is None:
            self._embed_rr = SimpleEmbedReranker(self.ollama.embed)

    def _apply_rerank(self, question: str, docs: List[str], metas: List[Dict[str, Any]], top_k: int) -> Tuple[List[str], List[Dict[str, Any]]]:
        self._ensure_rerankers()
        # Ưu tiên BGE ONNX nếu khả dụng; nếu lỗi thì fallback embedding
        if self._bge_rr and self._bge_rr.available():
            try:
                return self._bge_rr.rerank(question, docs, metas, top_k)
            except Exception:
                pass
        # Fallback
        assert self._embed_rr is not None
        return self._embed_rr.rerank(question, docs, metas, top_k)

    def _get_llm(self, provider: Optional[str] = None):
        name = (provider or self.default_provider or "ollama").lower()
        if name == "openai":
            if self._openai is None:
                try:
                    self._openai = OpenAIClient()
                except Exception:
                    self._openai = None
            return self._openai or self.ollama
        return self.ollama

    def generate_text(self, prompt: str, provider: Optional[str] = None) -> str:
        llm = self._get_llm(provider)
        return llm.generate(prompt)

    def generate_stream(self, prompt: str, provider: Optional[str] = None):
        llm = self._get_llm(provider)
        return llm.generate_stream(prompt)

    def answer(self, question: str, top_k: int = 5, method: str = "vector", bm25_weight: float = 0.5, rerank_enable: bool = False, rerank_top_n: int = 10, provider: Optional[str] = None, rrf_enable: Optional[bool] = None, rrf_k: Optional[int] = None) -> Dict[str, Any]:
        method = (method or "vector").lower()
        base_k = max(top_k, rerank_top_n if rerank_enable else top_k)
        if method == "bm25":
            retrieved = self.retrieve_bm25(question, top_k=base_k)
        elif method == "hybrid":
            retrieved = self.retrieve_hybrid(question, top_k=base_k, bm25_weight=bm25_weight, rrf_enable=rrf_enable, rrf_k=rrf_k)
        else:
            retrieved = self.retrieve(question, top_k=base_k)
        docs = retrieved.get("documents", [])
        metas = retrieved.get("metadatas", [])
        if rerank_enable and docs:
            docs, metas = self._apply_rerank(question, docs, metas, top_k)
        else:
            docs = docs[:top_k]
            metas = metas[:top_k]
        prompt = self.build_prompt(question, docs)
        reply = self.generate_text(prompt, provider=provider)
        return {
            "answer": reply,
            "contexts": docs,
            "metadatas": metas,
            "method": method,
            "bm25_weight": bm25_weight,
            "rerank_enable": rerank_enable,
            "rerank_top_n": rerank_top_n,
        }

    # ===== Multi-hop =====
    def _decompose(self, question: str, fanout: int = 2) -> List[str]:
        """Dùng LLM để đề xuất một số câu hỏi con ngắn gọn (JSON array).
        An toàn: ép model phải trả về JSON duy nhất; nếu parse thất bại, fallback 1 subquestion = original.
        """
        fanout = max(1, min(int(fanout or 1), 5))
        sys = (
            "Bạn là công cụ phân rã câu hỏi. Hãy trả về mảng JSON các câu hỏi con ngắn gọn (tiếng Việt), "
            "tối đa N phần tử. Chỉ in JSON, không thêm giải thích."
        )
        ins = (
            f"N={fanout}. Câu hỏi gốc: {question}\n"
            "Yêu cầu đầu ra: một mảng JSON thuần, ví dụ: [\"câu hỏi 1\", \"câu hỏi 2\"]."
        )
        prompt = f"[SYSTEM]\n{sys}\n[/SYSTEM]\n{ins}"
        try:
            raw = self.ollama.generate(prompt)
            # Tìm khối JSON array đầu tiên
            start = raw.find('[')
            end = raw.rfind(']')
            if start != -1 and end != -1 and end > start:
                arr_txt = raw[start:end+1]
                data = json.loads(arr_txt)
                subqs = [str(x) for x in data if isinstance(x, (str, int, float))]
                subqs = [s for s in subqs if s.strip()]
                if subqs:
                    return subqs[:fanout]
        except Exception:
            pass
        return [question]

    def answer_multihop(
        self,
        question: str,
        *,
        depth: int = 2,
        fanout: int = 2,
        top_k: int = 5,
        method: str = "hybrid",
        bm25_weight: float = 0.5,
        rerank_enable: bool = False,
        rerank_top_n: int = 10,
        skip_answer: bool = False,
        rrf_enable: Optional[bool] = None,
        rrf_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        depth = max(1, min(int(depth or 1), 3))
        fanout = max(1, min(int(fanout or 1), 3))
        agg_docs: List[str] = []
        agg_metas: List[Dict[str, Any]] = []
        seen_keys = set()
        subquestions_all: List[str] = []
        cur_questions = [question]
        # Duyệt theo tầng
        for _ in range(depth):
            next_questions: List[str] = []
            # Decompose mỗi câu hỏi hiện tại
            for q in cur_questions:
                subs = self._decompose(q, fanout=fanout)
                subquestions_all.extend(subs)
                next_questions.extend(subs)
            # Retrieve cho tất cả sub-qs của tầng này
            for sq in next_questions:
                base_k = max(top_k, rerank_top_n if rerank_enable else top_k)
                if method == "bm25":
                    retrieved = self.retrieve_bm25(sq, top_k=base_k)
                elif method == "hybrid":
                    retrieved = self.retrieve_hybrid(sq, top_k=base_k, bm25_weight=bm25_weight, rrf_enable=rrf_enable, rrf_k=rrf_k)
                else:
                    retrieved = self.retrieve(sq, top_k=base_k)
                docs = retrieved.get("documents", [])
                metas = retrieved.get("metadatas", [])
                for d, m in zip(docs, metas):
                    key = self._make_key(d, m)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    agg_docs.append(d)
                    agg_metas.append(m)
            cur_questions = next_questions
        # Fallback: nếu không thu được context nào qua multi-hop, thử single-hop trên câu hỏi gốc
        if not agg_docs:
            base_k = max(top_k, rerank_top_n if rerank_enable else top_k)
            if method == "bm25":
                retrieved = self.retrieve_bm25(question, top_k=base_k)
            elif method == "hybrid":
                retrieved = self.retrieve_hybrid(question, top_k=base_k, bm25_weight=bm25_weight)
            else:
                retrieved = self.retrieve(question, top_k=base_k)
            agg_docs = retrieved.get("documents", [])
            agg_metas = retrieved.get("metadatas", [])

        # Rerank/giới hạn top_k
        if rerank_enable and agg_docs:
            sel_docs, sel_metas = self._apply_rerank(question, agg_docs, agg_metas, top_k)
        else:
            sel_docs = agg_docs[:top_k]
            sel_metas = agg_metas[:top_k]
        prompt = self.build_prompt(question, sel_docs)
        reply = "" if skip_answer else self.generate_text(prompt, provider=None)
        return {
            "answer": reply,
            "contexts": sel_docs,
            "metadatas": sel_metas,
            "method": method,
            "bm25_weight": bm25_weight,
            "rerank_enable": rerank_enable,
            "rerank_top_n": rerank_top_n,
            "depth": depth,
            "fanout": fanout,
            "subquestions": subquestions_all,
        }
