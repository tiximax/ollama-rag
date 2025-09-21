from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import json

from .rag_engine import RagEngine
from .chat_store import ChatStore

app = FastAPI(title="Ollama RAG App")

# Khởi tạo engine với thiết lập Multi-DB (tương thích ngược)
# Nếu PERSIST_DIR được set (ví dụ data/chroma) sẽ dùng như db mặc định trong root của nó
# Nếu không, mặc định PERSIST_ROOT=data/kb và DB_NAME=default
engine = RagEngine(persist_dir=os.path.join("data", "chroma"))
chat_store = ChatStore(engine.persist_root)

# Phục vụ web UI
app.mount("/static", StaticFiles(directory="web"), name="static")


@app.get("/")
def root():
    return FileResponse("web/index.html")


class IngestRequest(BaseModel):
    paths: List[str] = ["data/docs"]
    db: str | None = None


@app.post("/api/ingest")
def api_ingest(req: IngestRequest):
    try:
        if req.db:
            engine.use_db(req.db)
        count = engine.ingest_paths(req.paths)
        return {"status": "ok", "chunks_indexed": count, "db": engine.db_name}
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


class MultiHopQueryRequest(BaseModel):
    query: str
    k: int = 5
    method: str = "hybrid"
    bm25_weight: float = 0.5
    rerank_enable: bool = False
    rerank_top_n: int = 10
    depth: int = 2
    fanout: int = 2
    rrf_enable: bool | None = None
    rrf_k: int | None = None
    rewrite_enable: bool = False
    rewrite_n: int = 2
    provider: Optional[str] = None
    chat_id: Optional[str] = None
    save_chat: bool = True
    db: str | None = None


@app.post("/api/query")
def api_query(req: QueryRequest):
    try:
        if req.db:
            engine.use_db(req.db)
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
        )
        # Lưu chat nếu cần
        if req.save_chat and req.chat_id:
            try:
                chat_store.append_pair(engine.db_name, req.chat_id, req.query, result.get("answer", ""), {"metas": result.get("metadatas", [])})
            except Exception:
                pass
        result["db"] = engine.db_name
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream_query")
def api_stream_query(req: QueryRequest):
    try:
        def gen():
            if req.db:
                engine.use_db(req.db)
            # Lấy contexts theo method đã chọn, có thể áp dụng reranker trước khi stream
            base_k = max(req.k, req.rerank_top_n if req.rerank_enable else req.k)
            retrieved = engine.retrieve_aggregate(
                req.query,
                top_k=base_k,
                method=req.method,
                bm25_weight=req.bm25_weight,
                rrf_enable=req.rrf_enable,
                rrf_k=req.rrf_k,
                rewrite_enable=req.rewrite_enable,
                rewrite_n=req.rewrite_n,
                provider=req.provider,
            )
            ctx_docs = retrieved["documents"]
            metas = retrieved["metadatas"]
            if req.rerank_enable and ctx_docs:
                # dùng hàm private trong engine để giữ logic nhất quán
                ctx_docs, metas = engine._apply_rerank(req.query, ctx_docs, metas, req.k)  # type: ignore[attr-defined]
            else:
                ctx_docs = ctx_docs[:req.k]
                metas = metas[:req.k]
            # Gửi contexts trước dưới dạng JSON đánh dấu
            header = {"contexts": ctx_docs, "metadatas": metas, "db": engine.db_name}
            yield "[[CTXJSON]]" + json.dumps(header) + "\n"
            prompt = engine.build_prompt(req.query, ctx_docs)
            answer_buf = []
            try:
                for chunk in engine.generate_stream(prompt, provider=req.provider):
                    answer_buf.append(chunk)
                    yield chunk
            except Exception:
                return
            finally:
                # Lưu chat nếu cần
                if req.save_chat and req.chat_id:
                    try:
                        chat_store.append_pair(engine.db_name, req.chat_id, req.query, "".join(answer_buf), {"metas": metas})
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
        )
        if req.save_chat and req.chat_id:
            try:
                chat_store.append_pair(engine.db_name, req.chat_id, req.query, result.get("answer", ""), {"metas": result.get("metadatas", [])})
            except Exception:
                pass
        result["db"] = engine.db_name
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream_multihop_query")
def api_stream_multihop_query(req: MultiHopQueryRequest):
    try:
        def gen():
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
                    ctx_docs, metas = engine._apply_rerank(req.query, ctx_docs, metas, req.k)  # type: ignore[attr-defined]
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
                        chat_store.append_pair(engine.db_name, req.chat_id, req.query, "".join(answer_buf), {"metas": metas})
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
