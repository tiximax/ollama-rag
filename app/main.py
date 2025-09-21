from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List
import os
import json

from .rag_engine import RagEngine

app = FastAPI(title="Ollama RAG App")

# Khởi tạo engine với thiết lập Multi-DB (tương thích ngược)
# Nếu PERSIST_DIR được set (ví dụ data/chroma) sẽ dùng như db mặc định trong root của nó
# Nếu không, mặc định PERSIST_ROOT=data/kb và DB_NAME=default
engine = RagEngine(persist_dir=os.path.join("data", "chroma"))

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
        )
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
            if req.method == "bm25":
                retrieved = engine.retrieve_bm25(req.query, top_k=base_k)
            elif req.method == "hybrid":
                retrieved = engine.retrieve_hybrid(req.query, top_k=base_k, bm25_weight=req.bm25_weight)
            else:
                retrieved = engine.retrieve(req.query, top_k=base_k)
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
            try:
                for chunk in engine.ollama.generate_stream(prompt):
                    yield chunk
            except Exception:
                # Kết thúc stream nhẹ nhàng nếu LLM stream gặp lỗi kết nối/timeout
                return
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
        )
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
                    retrieved = engine.retrieve_hybrid(req.query, top_k=base_k, bm25_weight=req.bm25_weight)
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
            try:
                for chunk in engine.ollama.generate_stream(prompt):
                    yield chunk
            except Exception:
                return
        return StreamingResponse(gen(), media_type="text/plain")
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
