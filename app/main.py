from fastapi import FastAPI, HTTPException, Response, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import json
import uuid

from .rag_engine import RagEngine
from .chat_store import ChatStore
from .feedback_store import FeedbackStore
from .exp_logger import ExperimentLogger

app = FastAPI(title="Ollama RAG App")

# Khởi tạo engine với thiết lập Multi-DB (tương thích ngược)
# Nếu PERSIST_DIR được set (ví dụ data/chroma) sẽ dùng như db mặc định trong root của nó
# Nếu không, mặc định PERSIST_ROOT=data/kb và DB_NAME=default
engine = RagEngine(persist_dir=os.path.join("data", "chroma"))
chat_store = ChatStore(engine.persist_root)
feedback_store = FeedbackStore(engine.persist_root)
exp_logger = ExperimentLogger(engine.persist_root)

# Phục vụ web UI
app.mount("/static", StaticFiles(directory="web"), name="static")


@app.get("/")
def root():
    return FileResponse("web/index.html")


class IngestRequest(BaseModel):
    paths: List[str] = ["data/docs"]
    db: str | None = None
    version: Optional[str] = None


@app.post("/api/ingest")
def api_ingest(req: IngestRequest):
    try:
        if req.db:
            engine.use_db(req.db)
        count = engine.ingest_paths(req.paths, version=req.version)
        return {"status": "ok", "chunks_indexed": count, "db": engine.db_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Upload & Ingest =====
@app.post("/api/upload")
async def api_upload(files: List[UploadFile] = File(...), db: Optional[str] = Form(None), version: Optional[str] = Form(None)):
    try:
        if db:
            engine.use_db(db)
        save_dir = os.path.join("data", "docs", "uploads")
        os.makedirs(save_dir, exist_ok=True)
        saved_paths: List[str] = []
        allowed = {".txt", ".pdf", ".docx"}
        for f in files:
            name = f.filename or ""
            ext = os.path.splitext(name)[1].lower()
            if ext not in allowed:
                continue
            data = await f.read()
            new_name = f"{uuid.uuid4().hex}{ext}"
            path = os.path.join(save_dir, new_name)
            with open(path, "wb") as out:
                out.write(data)
            saved_paths.append(path)
        count = engine.ingest_paths(saved_paths, version=version) if saved_paths else 0
        return {"status": "ok", "saved": [os.path.basename(p) for p in saved_paths], "chunks_indexed": count, "db": engine.db_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class QueryRequest(BaseModel):
    query: str
    k: int = 5
    method: str = "vector"  # vector | bm25 | hybrid
    bm25_weight: float = 0.5
    rerank_enable: bool = False
    rerank_top_n: int = 10
    rrf_enable: bool | None = None
    rrf_k: int | None = None
    rewrite_enable: bool = False
    rewrite_n: int = 2
    provider: Optional[str] = None
    chat_id: Optional[str] = None
    save_chat: bool = True
    db: str | None = None
    languages: Optional[List[str]] = None
    versions: Optional[List[str]] = None
    rr_provider: Optional[str] = None  # auto|bge|embed
    rr_max_k: Optional[int] = None
    rr_batch_size: Optional[int] = None
    rr_num_threads: Optional[int] = None


class MultiHopQueryRequest(BaseModel):
    query: str
    k: int = 5
    method: str = "hybrid"
    bm25_weight: float = 0.5
    rerank_enable: bool = False
    rerank_top_n: int = 10
    depth: int = 2
    fanout: int = 2
    fanout_first_hop: Optional[int] = None
    budget_ms: Optional[int] = None
    rrf_enable: bool | None = None
    rrf_k: int | None = None
    provider: Optional[str] = None
    chat_id: Optional[str] = None
    save_chat: bool = True
    db: str | None = None
    languages: Optional[List[str]] = None
    versions: Optional[List[str]] = None
    rr_provider: Optional[str] = None
    rr_max_k: Optional[int] = None
    rr_batch_size: Optional[int] = None
    rr_num_threads: Optional[int] = None


@app.post("/api/query")
def api_query(req: QueryRequest):
    try:
        if req.db:
            engine.use_db(req.db)
        import time as _t
        t0 = int(_t.time() * 1000)
        result = engine.answer(
            req.query,
            top_k=req.k,
            method=req.method,
            bm25_weight=req.bm25_weight,
            rerank_enable=req.rerank_enable,
            rerank_top_n=req.rerank_top_n,
            provider=req.provider,
            rrf_enable=req.rrf_enable,
            rrf_k=req.rrf_k,
            rewrite_enable=req.rewrite_enable,
            rewrite_n=req.rewrite_n,
            languages=req.languages,
            versions=req.versions,
            rr_provider=req.rr_provider,
            rr_max_k=req.rr_max_k,
            rr_batch_size=req.rr_batch_size,
            rr_num_threads=req.rr_num_threads,
        )
        # Lưu chat nếu cần
        if req.save_chat and req.chat_id:
            try:
                chat_store.append_pair(
                    engine.db_name,
                    req.chat_id,
                    req.query,
                    result.get("answer", ""),
                    {"metas": result.get("metadatas", []), "contexts": result.get("contexts", [])},
                )
            except Exception:
                pass
        result["db"] = engine.db_name
        # Log
        try:
            t1 = int(_t.time() * 1000)
            exp_logger.log(engine.db_name, {
                "ts": t1,
                "latency_ms": t1 - t0,
                "route": "/api/query",
                "db": engine.db_name,
                "provider": req.provider or engine.default_provider,
                "method": req.method,
                "k": req.k,
                "bm25_weight": req.bm25_weight,
                "rerank_enable": req.rerank_enable,
                "rerank_top_n": req.rerank_top_n,
                "rrf_enable": req.rrf_enable,
                "rrf_k": req.rrf_k,
                "rewrite_enable": req.rewrite_enable,
                "rewrite_n": req.rewrite_n,
                "languages": req.languages,
                "versions": req.versions,
                "query": req.query,
                "answer_len": len(result.get("answer", "")),
                "contexts_count": len(result.get("contexts", [])),
                "contexts_sources": [ (m or {}).get("source", "") for m in result.get("metadatas", []) ],
            })
        except Exception:
            pass
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream_query")
def api_stream_query(req: QueryRequest):
    try:
        def gen():
            import time as _t
            t0 = int(_t.time() * 1000)
            saved_early = False
            if req.db:
                engine.use_db(req.db)
            # Lấy contexts theo method đã chọn, có thể áp dụng reranker trước khi stream
            base_k = max(req.k, req.rerank_top_n if req.rerank_enable else req.k)
            if req.rewrite_enable:
                retrieved = engine.retrieve_aggregate(
                    req.query,
                    top_k=base_k,
                    method=req.method,
                    bm25_weight=req.bm25_weight,
                    rrf_enable=req.rrf_enable,
                    rrf_k=req.rrf_k,
                    rewrite_enable=True,
                    rewrite_n=req.rewrite_n,
                    provider=req.provider,
                    languages=req.languages,
                    versions=req.versions,
                )
            else:
                if req.method == "bm25":
                    retrieved = engine.retrieve_bm25(req.query, top_k=base_k, languages=req.languages, versions=req.versions)
                elif req.method == "hybrid":
                    retrieved = engine.retrieve_hybrid(req.query, top_k=base_k, bm25_weight=req.bm25_weight, rrf_enable=req.rrf_enable, rrf_k=req.rrf_k, languages=req.languages, versions=req.versions)
                else:
                    retrieved = engine.retrieve(req.query, top_k=base_k, languages=req.languages, versions=req.versions)
            ctx_docs = retrieved["documents"]
            metas = retrieved["metadatas"]
            # Fallback nếu không có contexts
            if not ctx_docs:
                try:
                    base_k = max(req.k, req.rerank_top_n if req.rerank_enable else req.k)
                    # Ưu tiên BM25 fallback
                    fb = engine.retrieve_bm25(req.query, top_k=base_k)
                    ctx_docs = fb.get("documents", [])
                    metas = fb.get("metadatas", [])
                    if not ctx_docs:
                        # Thử vector
                        fb2 = engine.retrieve(req.query, top_k=base_k)
                        ctx_docs = fb2.get("documents", [])
                        metas = fb2.get("metadatas", [])
                    if not ctx_docs:
                        # Lấy ít nhất 1 doc bất kỳ từ collection để hiển thị
                        try:
                            results = engine.collection.get(include=["documents", "metadatas"])  # type: ignore[arg-type]
                            docs_any = results.get("documents", [])
                            metas_any = results.get("metadatas", [])
                            if docs_any:
                                ctx_docs = [docs_any[0]]
                                metas = [metas_any[0] if metas_any else {}]
                        except Exception:
                            pass
                except Exception:
                    pass
            if req.rerank_enable and ctx_docs:
                # dùng hàm private trong engine để giữ logic nhất quán
                ctx_docs, metas = engine._apply_rerank(req.query, ctx_docs, metas, req.k, rr_provider=req.rr_provider, rr_max_k=req.rr_max_k, rr_batch_size=req.rr_batch_size, rr_num_threads=req.rr_num_threads)  # type: ignore[attr-defined]
            else:
                ctx_docs = ctx_docs[:req.k]
                metas = metas[:req.k]
            # Gửi contexts trước dưới dạng JSON đánh dấu
            header = {"contexts": ctx_docs, "metadatas": metas, "db": engine.db_name}
            yield "[[CTXJSON]]" + json.dumps(header) + "\n"
            # Lưu chat sớm (trả lời rỗng) ngay sau khi có contexts (giúp analytics và test nhanh)
            if req.save_chat and req.chat_id and not saved_early:
                try:
                    chat_store.append_pair(engine.db_name, req.chat_id, req.query, "", {"metas": metas})
                    saved_early = True
                except Exception:
                    saved_early = False
            # Log sớm ngay sau khi có contexts để export logs không phải đợi sinh câu trả lời
            try:
                exp_logger.log(engine.db_name, {
                    "ts": int(__import__('time').time() * 1000),
                    "latency_ms": 0,
                    "route": "/api/stream_query",
                    "db": engine.db_name,
                    "provider": req.provider or engine.default_provider,
                    "method": req.method,
                    "k": req.k,
                    "bm25_weight": req.bm25_weight,
                    "rerank_enable": req.rerank_enable,
                    "rerank_top_n": req.rerank_top_n,
                    "rrf_enable": req.rrf_enable,
                    "rrf_k": req.rrf_k,
                    "rewrite_enable": req.rewrite_enable,
                    "rewrite_n": req.rewrite_n,
                    "languages": req.languages,
                    "versions": req.versions,
                    "query": req.query,
                    "answer_len": 0,
                    "contexts_count": len(ctx_docs or []),
                    "contexts_sources": [ (m or {}).get("source", "") for m in metas or [] ],
                })
            except Exception:
                pass
            prompt = engine.build_prompt(req.query, ctx_docs)
            answer_buf = []
            try:
                for chunk in engine.generate_stream(prompt, provider=req.provider):
                    answer_buf.append(chunk)
                    yield chunk
            except Exception:
                return
            finally:
                # Lưu chat nếu cần (nếu chưa lưu sớm)
                if req.save_chat and req.chat_id and not saved_early:
                    try:
                        chat_store.append_pair(engine.db_name, req.chat_id, req.query, "".join(answer_buf), {"metas": metas, "contexts": ctx_docs})
                    except Exception:
                        pass
                # Log
                try:
                    t1 = int(_t.time() * 1000)
                    exp_logger.log(engine.db_name, {
                        "ts": t1,
                        "latency_ms": t1 - t0,
                        "route": "/api/stream_query",
                        "db": engine.db_name,
                        "provider": req.provider or engine.default_provider,
                        "method": req.method,
                        "k": req.k,
                        "bm25_weight": req.bm25_weight,
                        "rerank_enable": req.rerank_enable,
                        "rerank_top_n": req.rerank_top_n,
                        "rrf_enable": req.rrf_enable,
                        "rrf_k": req.rrf_k,
                        "rewrite_enable": req.rewrite_enable,
                        "rewrite_n": req.rewrite_n,
                        "languages": req.languages,
                        "versions": req.versions,
                        "query": req.query,
                        "answer_len": len("".join(answer_buf)),
                        "contexts_count": len(ctx_docs or []),
                        "contexts_sources": [ (m or {}).get("source", "") for m in metas or [] ],
                    })
                except Exception:
                    pass
        return StreamingResponse(gen(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/multihop_query")
def api_multihop_query(req: MultiHopQueryRequest):
    try:
        if req.db:
            engine.use_db(req.db)
        import time as _t
        t0 = int(_t.time() * 1000)
        result = engine.answer_multihop(
            req.query,
            depth=req.depth,
            fanout=req.fanout,
            top_k=req.k,
            method=req.method,
            bm25_weight=req.bm25_weight,
            rerank_enable=req.rerank_enable,
            rerank_top_n=req.rerank_top_n,
            skip_answer=True,
            rrf_enable=req.rrf_enable,
            rrf_k=req.rrf_k,
            fanout_first_hop=req.fanout_first_hop,
            budget_ms=req.budget_ms,
            languages=req.languages,
            versions=req.versions,
        )
        if req.save_chat and req.chat_id:
            try:
                chat_store.append_pair(engine.db_name, req.chat_id, req.query, result.get("answer", ""), {"metas": result.get("metadatas", []), "contexts": result.get("contexts", [])})
            except Exception:
                pass
        result["db"] = engine.db_name
        # Log
        try:
            t1 = int(_t.time() * 1000)
            result_metas = result.get("metadatas", [])
            exp_logger.log(engine.db_name, {
                "ts": t1,
                "latency_ms": t1 - t0,
                "route": "/api/multihop_query",
                "db": engine.db_name,
                "provider": req.provider or engine.default_provider,
                "method": req.method,
                "k": req.k,
                "bm25_weight": req.bm25_weight,
                "rerank_enable": req.rerank_enable,
                "rerank_top_n": req.rerank_top_n,
                "rrf_enable": req.rrf_enable,
                "rrf_k": req.rrf_k,
                "depth": req.depth,
                "fanout": req.fanout,
                "fanout_first_hop": req.fanout_first_hop,
                "budget_ms": req.budget_ms,
                "languages": req.languages,
                "versions": req.versions,
                "query": req.query,
                "answer_len": len(result.get("answer", "")),
                "contexts_count": len(result.get("contexts", [])),
                "contexts_sources": [ (m or {}).get("source", "") for m in result_metas ],
            })
        except Exception:
            pass
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream_multihop_query")
def api_stream_multihop_query(req: MultiHopQueryRequest):
    try:
        def gen():
            import time as _t
            t0 = int(_t.time() * 1000)
            if req.db:
                engine.use_db(req.db)
            # Chuẩn bị contexts qua multi-hop (không stream decomposition để đơn giản)
            mh = engine.answer_multihop(
                req.query,
                depth=req.depth,
                fanout=req.fanout,
                top_k=req.k,
                method=req.method,
                bm25_weight=req.bm25_weight,
                rerank_enable=req.rerank_enable,
                rerank_top_n=req.rerank_top_n,
                skip_answer=True,
                fanout_first_hop=req.fanout_first_hop,
                budget_ms=req.budget_ms,
                languages=req.languages,
                versions=req.versions,
            )
            ctx_docs = mh.get("contexts", [])
            metas = mh.get("metadatas", [])
            # Nếu multi-hop không thu được contexts, fallback về single-hop theo method
            if not ctx_docs:
                base_k = max(req.k, req.rerank_top_n if req.rerank_enable else req.k)
                if req.method == "bm25":
                    retrieved = engine.retrieve_bm25(req.query, top_k=base_k)
                elif req.method == "hybrid":
                    retrieved = engine.retrieve_hybrid(req.query, top_k=base_k, bm25_weight=req.bm25_weight, rrf_enable=req.rrf_enable, rrf_k=req.rrf_k)
                else:
                    retrieved = engine.retrieve(req.query, top_k=base_k)
                ctx_docs = retrieved.get("documents", [])
                metas = retrieved.get("metadatas", [])
                if req.rerank_enable and ctx_docs:
                    ctx_docs, metas = engine._apply_rerank(req.query, ctx_docs, metas, req.k, rr_provider=req.rr_provider, rr_max_k=req.rr_max_k, rr_batch_size=req.rr_batch_size, rr_num_threads=req.rr_num_threads)  # type: ignore[attr-defined]
                else:
                    ctx_docs = ctx_docs[:req.k]
                    metas = metas[:req.k]
            header = {"contexts": ctx_docs, "metadatas": metas, "db": engine.db_name}
            yield "[[CTXJSON]]" + json.dumps(header) + "\n"
            # Stream phần trả lời chính thức dựa trên prompt đã dùng
            prompt = engine.build_prompt(req.query, ctx_docs)
            answer_buf = []
            try:
                for chunk in engine.generate_stream(prompt, provider=req.provider):
                    answer_buf.append(chunk)
                    yield chunk
            except Exception:
                return
            finally:
                if req.save_chat and req.chat_id:
                    try:
                        chat_store.append_pair(engine.db_name, req.chat_id, req.query, "".join(answer_buf), {"metas": metas, "contexts": ctx_docs})
                    except Exception:
                        pass
                # Log
                try:
                    t1 = int(_t.time() * 1000)
                    exp_logger.log(engine.db_name, {
                        "ts": t1,
                        "latency_ms": t1 - t0,
                        "route": "/api/stream_multihop_query",
                        "db": engine.db_name,
                        "provider": req.provider or engine.default_provider,
                        "method": req.method,
                        "k": req.k,
                        "bm25_weight": req.bm25_weight,
                        "rerank_enable": req.rerank_enable,
                        "rerank_top_n": req.rerank_top_n,
                        "depth": req.depth,
                        "fanout": req.fanout,
                        "fanout_first_hop": req.fanout_first_hop,
                        "budget_ms": req.budget_ms,
                        "query": req.query,
                        "answer_len": len("".join(answer_buf)),
                        "contexts_count": len(ctx_docs or []),
                        "contexts_sources": [ (m or {}).get("source", "") for m in metas or [] ],
                    })
                except Exception:
                    pass
        return StreamingResponse(gen(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Chat APIs =====
class ChatCreate(BaseModel):
    db: Optional[str] = None
    name: Optional[str] = None

class ChatRename(BaseModel):
    name: str

@app.get("/api/chats")
def api_chats_list(db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        return {"db": engine.db_name, "chats": chat_store.list(engine.db_name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chats")
def api_chats_create(req: ChatCreate):
    try:
        if req.db:
            engine.use_db(req.db)
        data = chat_store.create(engine.db_name, name=req.name)
        return {"db": engine.db_name, "chat": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Define search BEFORE dynamic {chat_id} routes to avoid conflicts
@app.get("/api/chats/search")
def api_chats_search(q: str, db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        return {"db": engine.db_name, "results": chat_store.search(engine.db_name, q)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chats/export_db")
def api_chats_export_db(format: str = "json", db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        data = chat_store.export_db_zip(engine.db_name, fmt=format)
        from datetime import datetime
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        filename = f"{engine.db_name}-chats-{ts}.zip"
        return Response(content=data, media_type="application/zip", headers={
            "Content-Disposition": f"attachment; filename={filename}"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chats/{chat_id}")
def api_chats_get(chat_id: str, db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        data = chat_store.get(engine.db_name, chat_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/chats/{chat_id}")
def api_chats_rename(chat_id: str, req: ChatRename, db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        data = chat_store.rename(engine.db_name, chat_id, req.name)
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chats/{chat_id}")
def api_chats_delete(chat_id: str, db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        chat_store.delete(engine.db_name, chat_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chats")
def api_chats_delete_all(db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        cnt = chat_store.delete_all(engine.db_name)
        return {"status": "ok", "deleted": cnt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chats/{chat_id}/export")
def api_chats_export(chat_id: str, format: str = "json", db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        fmt = (format or "json").lower()
        if fmt == "md" or fmt == "markdown":
            md = chat_store.export_markdown(engine.db_name, chat_id)
            if md is None:
                raise HTTPException(status_code=404, detail="Chat not found")
            return Response(content=md, media_type="text/markdown")
        # default json
        data = chat_store.export_json(engine.db_name, chat_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Provider APIs =====
class ProviderName(BaseModel):
    name: str

# ===== Filters API =====
@app.get("/api/filters")
def api_get_filters(db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        return engine.get_filters()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Docs APIs =====
class DocsDeleteRequest(BaseModel):
    sources: List[str]
    db: Optional[str] = None


@app.get("/api/docs")
def api_docs_list(db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        return {"db": engine.db_name, "docs": engine.list_sources()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/docs")
def api_docs_delete(req: DocsDeleteRequest):
    try:
        if req.db:
            engine.use_db(req.db)
        n = engine.delete_sources(req.sources or [])
        return {"status": "ok", "deleted_sources": n, "db": engine.db_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Offline Evaluation API =====
class EvalQueryItem(BaseModel):
    query: str
    expected_sources: Optional[List[str]] = None  # match by substring in metadata.source
    expected_substrings: Optional[List[str]] = None  # match by substring in retrieved docs
    languages: Optional[List[str]] = None
    versions: Optional[List[str]] = None

class EvalRequest(BaseModel):
    queries: List[EvalQueryItem]
    k: int = 5
    method: str = "bm25"
    bm25_weight: float = 0.5
    rerank_enable: bool = False
    rerank_top_n: int = 10
    rrf_enable: bool | None = None
    rrf_k: int | None = None
    rewrite_enable: bool = False
    rewrite_n: int = 2
    provider: Optional[str] = None
    db: Optional[str] = None
    # defaults for all items if not provided per-item
    languages: Optional[List[str]] = None
    versions: Optional[List[str]] = None

@app.post("/api/eval/offline")
def api_eval_offline(req: EvalRequest):
    try:
        if req.db:
            engine.use_db(req.db)
        total = len(req.queries or [])
        hits = 0
        details: List[Dict[str, Any]] = []
        for item in req.queries:
            langs = item.languages if item.languages is not None else req.languages
            vers = item.versions if item.versions is not None else req.versions
            base_k = max(req.k, req.rerank_top_n if req.rerank_enable else req.k)
            retrieved = engine.retrieve_aggregate(
                item.query,
                top_k=base_k,
                method=req.method,
                bm25_weight=req.bm25_weight,
                rrf_enable=req.rrf_enable,
                rrf_k=req.rrf_k,
                rewrite_enable=req.rewrite_enable,
                rewrite_n=req.rewrite_n,
                provider=req.provider,
                languages=langs,
                versions=vers,
            )
            docs = retrieved.get("documents", [])
            metas = retrieved.get("metadatas", [])
            if req.rerank_enable and docs:
                docs, metas = engine._apply_rerank(item.query, docs, metas, req.k)  # type: ignore[attr-defined]
            else:
                docs = docs[:req.k]
                metas = metas[:req.k]
            # Prepare for matching
            srcs: List[str] = []
            for m in metas:
                try:
                    s = str(m.get("source", ""))
                except Exception:
                    s = ""
                srcs.append(s)
            matched_srcs: List[str] = []
            matched_subs: List[str] = []
            # Match sources by substring anywhere in path
            if item.expected_sources:
                for exp in item.expected_sources:
                    exp = (exp or "").strip()
                    if not exp:
                        continue
                    if any(exp in s for s in srcs):
                        matched_srcs.append(exp)
            # Match expected substrings in any retrieved doc
            if item.expected_substrings:
                for exp in item.expected_substrings:
                    exp = (exp or "").strip()
                    if not exp:
                        continue
                    if any(exp.lower() in (d or "").lower() for d in docs):
                        matched_subs.append(exp)
            matched = bool(matched_srcs or matched_subs)
            if matched:
                hits += 1
            details.append({
                "query": item.query,
                "matched": matched,
                "matched_sources": matched_srcs,
                "matched_substrings": matched_subs,
                "retrieved_sources": srcs,
            })
        recall = (hits / total) if total > 0 else 0.0
        return {"db": engine.db_name, "n": total, "hits": hits, "recall_at_k": recall, "details": details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Logs APIs =====
class LogsEnableReq(BaseModel):
    db: Optional[str] = None
    enabled: bool

@app.get("/api/logs/info")
def api_logs_info(db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        return exp_logger.info(engine.db_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs/enable")
def api_logs_enable(req: LogsEnableReq):
    try:
        if req.db:
            engine.use_db(req.db)
        return exp_logger.enable(engine.db_name, req.enabled)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/export")
def api_logs_export(db: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        content = exp_logger.export(engine.db_name, since=since, until=until)
        from datetime import datetime as _dt, timezone as _tz
        ts = _dt.now(_tz.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"logs-{engine.db_name}-{ts}.jsonl"
        return Response(content=content, media_type="application/jsonl", headers={
            "Content-Disposition": f"attachment; filename={filename}"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/logs")
def api_logs_clear(db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        cnt = exp_logger.clear(engine.db_name)
        return {"status": "ok", "deleted_files": cnt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/summary")
def api_logs_summary(db: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None):
    """Tóm tắt nhanh logs JSONL: tổng số, median latency, contexts_rate, phân bố theo route/provider/method."""
    try:
        if db:
            engine.use_db(db)
        raw = exp_logger.export(engine.db_name, since=since, until=until)
        import json, statistics as stats
        total = 0
        latencies: list[float] = []
        with_ctx = 0
        by_route: dict[str,int] = {}
        by_provider: dict[str,int] = {}
        by_method: dict[str,int] = {}
        first_ts = None
        last_ts = None
        for line in raw.splitlines():
            try:
                e = json.loads(line)
            except Exception:
                continue
            total += 1
            try:
                lat = float(e.get('latency_ms') or 0)
                if lat > 0:
                    latencies.append(lat)
            except Exception:
                pass
            try:
                if (e.get('contexts_count') or 0) > 0:
                    with_ctx += 1
            except Exception:
                pass
            r = str(e.get('route') or '')
            if r:
                by_route[r] = by_route.get(r, 0) + 1
            p = str(e.get('provider') or '')
            if p:
                by_provider[p] = by_provider.get(p, 0) + 1
            m = str(e.get('method') or '')
            if m:
                by_method[m] = by_method.get(m, 0) + 1
            ts = e.get('ts')
            if isinstance(ts, (int, float)):
                if first_ts is None or ts < first_ts: first_ts = ts
                if last_ts is None or ts > last_ts: last_ts = ts
        median = float(stats.median(latencies)) if latencies else 0.0
        rate = (with_ctx/total) if total > 0 else 0.0
        def top_k(d: dict[str,int], k: int = 5):
            return sorted([{ 'key': k_, 'count': v_ } for k_, v_ in d.items()], key=lambda x: x['count'], reverse=True)[:k]
        return {
            'db': engine.db_name,
            'total': total,
            'median_latency_ms': median,
            'contexts_rate': rate,
            'by_route': top_k(by_route),
            'by_provider': top_k(by_provider),
            'by_method': top_k(by_method),
            'first_ts': first_ts,
            'last_ts': last_ts,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Citations Export APIs =====
@app.get("/api/citations/chat/{chat_id}")
def api_citations_chat(chat_id: str, format: str = "json", db: Optional[str] = None, sources: Optional[str] = None, versions: Optional[str] = None, languages: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        data = chat_store.get(engine.db_name, chat_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        # build citations from assistant messages
        import re
        citations = []
        last_user = None
        for m in data.get('messages', []):
            role = m.get('role')
            if role == 'user':
                last_user = m.get('content')
                continue
            if role != 'assistant':
                continue
            ans = m.get('content') or ''
            metas = (m.get('meta') or {}).get('metas') or []
            ctxs = (m.get('meta') or {}).get('contexts') or []
            seen = set()
            for match in re.finditer(r"\[(\d+)\]", ans):
                try:
                    n = int(match.group(1))
                except Exception:
                    continue
                if n in seen or n <= 0 or n > len(metas):
                    continue
                seen.add(n)
                md = metas[n-1] or {}
                citations.append({
                    'n': n,
                    'source': md.get('source'),
                    'version': md.get('version'),
                    'language': md.get('language'),
                    'chunk': md.get('chunk'),
                    'excerpt': (ctxs[n-1] if 0 <= (n-1) < len(ctxs) else None),
                    'question': last_user,
                    'ts': m.get('ts'),
                })
        # apply filters
        def parse_csv(s: Optional[str]):
            if not s: return []
            return [x.strip() for x in s.split(',') if x.strip()]
        src_filters = parse_csv(sources)
        ver_filters = parse_csv(versions)
        lang_filters = parse_csv(languages)
        def keep(c):
            if src_filters:
                src = str(c.get('source') or '')
                if not any(f in src for f in src_filters):
                    return False
            if ver_filters:
                if str(c.get('version') or '') not in ver_filters:
                    return False
            if lang_filters:
                if str(c.get('language') or '') not in lang_filters:
                    return False
            return True
        citations = [c for c in citations if keep(c)]
        fmt = (format or 'json').lower()
        if fmt == 'csv':
            import io, csv
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=['n','source','version','language','chunk','question','excerpt','ts'])
            writer.writeheader()
            for row in citations:
                writer.writerow(row)
            return Response(content=buf.getvalue(), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename=citations-{chat_id}.csv'})
        if fmt == 'md' or fmt == 'markdown':
            lines = ['# Citations']
            for c in citations:
                lines.append(f"- [{c.get('n')}] {c.get('source')} v={c.get('version')} lang={c.get('language')} chunk={c.get('chunk')}")
            md = "\n".join(lines)
            return Response(content=md, media_type='text/markdown')
        # default json
        return citations
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/citations/db")
def api_citations_db(format: str = 'json', db: Optional[str] = None, sources: Optional[str] = None, versions: Optional[str] = None, languages: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        # Build per-chat files and zip strictly from JSON citations for consistency
        import io, zipfile, json
        mem = io.BytesIO()
        fmt = (format or 'json').lower()
        with zipfile.ZipFile(mem, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for ch in chat_store.list(engine.db_name):
                cid = ch.get('id')
                if not cid:
                    continue
                # Always get JSON rows first, then render per requested format
                rows = api_citations_chat(cid, format='json', db=engine.db_name, sources=sources, versions=versions, languages=languages)  # type: ignore[arg-type]
                rows = rows if isinstance(rows, list) else []
                fname_base = ch.get('name') or cid
                if fmt == 'csv':
                    import csv
                    from io import StringIO
                    s = StringIO()
                    w = csv.DictWriter(s, fieldnames=['n','source','version','language','chunk','question','excerpt','ts'])
                    w.writeheader()
                    for r in rows:
                        w.writerow(r)
                    zf.writestr(f"{fname_base}-citations.csv", s.getvalue())
                elif fmt in ('md','markdown'):
                    lines = ['# Citations']
                    for c in rows:
                        lines.append(f"- [{c.get('n')}] {c.get('source')} v={c.get('version')} lang={c.get('language')} chunk={c.get('chunk')}")
                    zf.writestr(f"{fname_base}-citations.md", "\n".join(lines))
                else:
                    zf.writestr(f"{fname_base}-citations.json", json.dumps(rows, ensure_ascii=False, indent=2))
        mem.seek(0)
        return Response(content=mem.read(), media_type='application/zip', headers={'Content-Disposition': f'attachment; filename={engine.db_name}-citations.zip'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Analytics APIs =====
class AnalyticsSummary(BaseModel):
    chats: int
    qa_pairs: int
    answered: int
    with_contexts: int
    answer_len_avg: float
    answer_len_median: float
    top_sources: List[Dict[str, Any]]
    top_versions: List[Dict[str, Any]]
    top_languages: List[Dict[str, Any]]
    first_ts: Optional[str] = None
    last_ts: Optional[str] = None

def _compute_chat_summary(chat: Dict[str, Any]) -> Dict[str, Any]:
    msgs = chat.get('messages', []) or []
    qa = 0
    answered = 0
    with_ctx = 0
    ans_lens: List[int] = []  # type: ignore[name-defined]
    src_counts: Dict[str, int] = {}
    ver_counts: Dict[str, int] = {}
    lang_counts: Dict[str, int] = {}
    first_ts: Optional[str] = None
    last_ts: Optional[str] = None
    for m in msgs:
        ts = m.get('ts')
        if isinstance(ts, str):
            if first_ts is None or ts < first_ts: first_ts = ts
            if last_ts is None or ts > last_ts: last_ts = ts
        if m.get('role') == 'assistant':
            qa += 1
            a = m.get('content') or ''
            if a.strip():
                answered += 1
                ans_lens.append(len(a))
            meta = m.get('meta') or {}
            metas = meta.get('metas') or []
            if isinstance(metas, list) and metas:
                with_ctx += 1
                for md in metas:
                    src = str((md or {}).get('source', '') or '')
                    if src:
                        src_counts[src] = src_counts.get(src, 0) + 1
                    ver = str((md or {}).get('version', '') or '')
                    if ver:
                        ver_counts[ver] = ver_counts.get(ver, 0) + 1
                    lang = str((md or {}).get('language', '') or '')
                    if lang:
                        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    import statistics as stats  # type: ignore
    avg = float(sum(ans_lens)/len(ans_lens)) if ans_lens else 0.0
    med = float(stats.median(ans_lens)) if ans_lens else 0.0
    def top_k(d: Dict[str, int], k: int = 5) -> List[Dict[str, Any]]:
        items = sorted(d.items(), key=lambda x: x[1], reverse=True)[:k]
        return [{ 'value': k_, 'count': v_ } for (k_, v_) in items]
    return {
        'qa_pairs': qa,
        'answered': answered,
        'with_contexts': with_ctx,
        'answer_len_avg': avg,
        'answer_len_median': med,
        'top_sources': top_k(src_counts),
        'top_versions': top_k(ver_counts),
        'top_languages': top_k(lang_counts),
        'first_ts': first_ts,
        'last_ts': last_ts,
    }

@app.get("/api/analytics/db")
def api_analytics_db(db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        chats = chat_store.list(engine.db_name)
        merged = {
            'chats': len(chats), 'qa_pairs': 0, 'answered': 0, 'with_contexts': 0,
            'answer_len_sum': 0.0, 'answer_len_count': 0, 'all_lens': [],
            'src': {}, 'ver': {}, 'lang': {}, 'first_ts': None, 'last_ts': None,
        }
        for ch in chats:
            data = chat_store.get(engine.db_name, ch.get('id'))
            if not data:
                continue
            s = _compute_chat_summary(data)
            merged['qa_pairs'] += s['qa_pairs']
            merged['answered'] += s['answered']
            merged['with_contexts'] += s['with_contexts']
            if s['answer_len_avg'] and s['answered']:
                merged['answer_len_sum'] += s['answer_len_avg'] * s['answered']
                merged['answer_len_count'] += s['answered']
            merged['all_lens'].extend([0]*0)  # placeholder, không dùng median tổng hợp tại đây
            for item in s['top_sources']:
                v = item['value']; c = int(item['count'])
                merged['src'][v] = merged['src'].get(v, 0) + c
            for item in s['top_versions']:
                v = item['value']; c = int(item['count'])
                merged['ver'][v] = merged['ver'].get(v, 0) + c
            for item in s['top_languages']:
                v = item['value']; c = int(item['count'])
                merged['lang'][v] = merged['lang'].get(v, 0) + c
            ft = s.get('first_ts'); lt = s.get('last_ts')
            if ft and (merged['first_ts'] is None or ft < merged['first_ts']): merged['first_ts'] = ft
            if lt and (merged['last_ts'] is None or lt > merged['last_ts']): merged['last_ts'] = lt
        avg = (merged['answer_len_sum']/merged['answer_len_count']) if merged['answer_len_count'] else 0.0
        def top_k(d: Dict[str, int], k: int = 5) -> List[Dict[str, Any]]:
            items = sorted(d.items(), key=lambda x: x[1], reverse=True)[:k]
            return [{ 'value': k_, 'count': v_ } for (k_, v_) in items]
        return {
            'db': engine.db_name,
            'chats': merged['chats'],
            'qa_pairs': merged['qa_pairs'],
            'answered': merged['answered'],
            'with_contexts': merged['with_contexts'],
            'answer_len_avg': float(avg),
            'answer_len_median': None,  # không tính median gộp
            'top_sources': top_k(merged['src']),
            'top_versions': top_k(merged['ver']),
            'top_languages': top_k(merged['lang']),
            'first_ts': merged['first_ts'],
            'last_ts': merged['last_ts'],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/chat/{chat_id}")
def api_analytics_chat(chat_id: str, db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        data = chat_store.get(engine.db_name, chat_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        s = _compute_chat_summary(data)
        out = {'db': engine.db_name, 'chat_id': chat_id}
        out.update(s)
        return out
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/provider")
def api_get_provider():
    try:
        return {"provider": engine.default_provider}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/provider")
def api_set_provider(req: ProviderName):
    try:
        name = (req.name or "ollama").lower()
        if name not in ("ollama", "openai"):
            raise HTTPException(status_code=400, detail="Invalid provider")
        engine.default_provider = name
        return {"provider": engine.default_provider}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Health API =====
@app.get("/api/health")
def api_health():
    """Trả trạng thái backend mở rộng: Ollama/OpenAI, models, và gợi ý khắc phục."""
    try:
        from .ollama_client import OLLAMA_BASE_URL, LLM_MODEL, EMBED_MODEL  # type: ignore
        import requests  # type: ignore
        import os as _os
        
        status = {
            "provider": engine.default_provider,
            "db": engine.db_name,
            "overall_status": "unknown",  # ok, warning, error
            "message": "",
            "suggestions": [],
            "test_mode": bool((_os.getenv("TEST_MODE") or "").strip()),
            "ollama": {
                "base_url": OLLAMA_BASE_URL,
                "ok": False,
                "error": None,
                "models": {"available": [], "required": [LLM_MODEL, EMBED_MODEL], "missing": []}
            },
            "openai": {"configured": False, "ok": False, "error": None},
        }
        
        # Check Ollama
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            if r.ok:
                status["ollama"]["ok"] = True
                try:
                    tags_data = r.json()
                    available_models = [m.get("name", "").split(":")[0] for m in tags_data.get("models", [])]
                    status["ollama"]["models"]["available"] = list(set(available_models))
                    
                    # Check required models
                    required = [LLM_MODEL.split(":")[0], EMBED_MODEL.split(":")[0]]
                    missing = [m for m in required if m not in available_models]
                    status["ollama"]["models"]["missing"] = missing
                    
                    if missing:
                        status["ollama"]["error"] = f"Thiếu models: {', '.join(missing)}"
                        status["ollama"]["ok"] = False
                except Exception:
                    status["ollama"]["error"] = "Không đọc được danh sách models"
                    status["ollama"]["ok"] = False
            else:
                status["ollama"]["error"] = f"HTTP {r.status_code}"
        except Exception as e:
            status["ollama"]["error"] = str(e)
        
        # Check OpenAI config
        if (_os.getenv("OPENAI_API_KEY") or "").strip():
            status["openai"]["configured"] = True
            status["openai"]["ok"] = True
        
        # Determine overall status and suggestions
        provider = status["provider"].lower()
        if provider == "ollama":
            if status["ollama"]["ok"]:
                status["overall_status"] = "ok"
                status["message"] = "Ollama sẵn sàng"
            elif "Thiếu models" in (status["ollama"].get("error") or ""):
                status["overall_status"] = "warning"
                status["message"] = "Ollama thiếu models"
                missing = status["ollama"]["models"]["missing"]
                status["suggestions"] = [f"Chạy: ollama pull {m}" for m in missing]
            else:
                status["overall_status"] = "error"
                status["message"] = "Ollama không khả dụng"
                status["suggestions"] = ["Chạy: ollama serve", "Hoặc đổi Provider sang OpenAI"]
        elif provider == "openai":
            if status["openai"]["ok"]:
                status["overall_status"] = "ok"
                status["message"] = "OpenAI sẵn sàng"
            else:
                status["overall_status"] = "error"
                status["message"] = "OpenAI chưa cấu hình"
                status["suggestions"] = ["Set biến môi trường OPENAI_API_KEY", "Hoặc đổi Provider sang Ollama"]
        else:
            status["overall_status"] = "error"
            status["message"] = "Provider không hợp lệ"
            status["suggestions"] = ["Chọn Provider: Ollama hoặc OpenAI"]
        
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Feedback APIs =====
class FeedbackItem(BaseModel):
    db: Optional[str] = None
    chat_id: Optional[str] = None
    query: Optional[str] = None
    answer: Optional[str] = None
    score: int  # -1 | 0 | 1
    comment: Optional[str] = None
    provider: Optional[str] = None
    method: Optional[str] = None
    k: Optional[int] = None
    languages: Optional[List[str]] = None
    versions: Optional[List[str]] = None
    sources: Optional[List[str]] = None

@app.post("/api/feedback")
def api_feedback_add(item: FeedbackItem):
    try:
        if item.db:
            engine.use_db(item.db)
        data = item.model_dump()
        data["db"] = engine.db_name
        feedback_store.append(engine.db_name, data)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/feedback")
def api_feedback_list(db: Optional[str] = None, limit: int = 50):
    try:
        if db:
            engine.use_db(db)
        items = feedback_store.list(engine.db_name, limit=limit)
        return {"db": engine.db_name, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/feedback")
def api_feedback_clear(db: Optional[str] = None):
    try:
        if db:
            engine.use_db(db)
        cnt = feedback_store.clear(engine.db_name)
        return {"status": "ok", "deleted": cnt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Multi-DB APIs =====
class DbName(BaseModel):
    name: str


@app.get("/api/dbs")
def api_list_dbs():
    try:
        return {"current": engine.db_name, "dbs": engine.list_dbs()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dbs/use")
def api_use_db(req: DbName):
    try:
        current = engine.use_db(req.name)
        return {"current": current, "dbs": engine.list_dbs()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dbs/create")
def api_create_db(req: DbName):
    try:
        engine.create_db(req.name)
        return {"status": "ok", "current": engine.db_name, "dbs": engine.list_dbs()}
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/dbs/{name}")
def api_delete_db(name: str):
    try:
        engine.delete_db(name)
        return {"status": "ok", "current": engine.db_name, "dbs": engine.list_dbs()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
