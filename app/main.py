from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List
import os
import json

from .rag_engine import RagEngine

app = FastAPI(title="Ollama RAG App")

# Khởi tạo engine với thư mục persist mặc định
engine = RagEngine(persist_dir=os.path.join("data", "chroma"))

# Phục vụ web UI
app.mount("/static", StaticFiles(directory="web"), name="static")


@app.get("/")
def root():
    return FileResponse("web/index.html")


class IngestRequest(BaseModel):
    paths: List[str] = ["data/docs"]


@app.post("/api/ingest")
def api_ingest(req: IngestRequest):
    try:
        count = engine.ingest_paths(req.paths)
        return {"status": "ok", "chunks_indexed": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class QueryRequest(BaseModel):
    query: str
    k: int = 5
    method: str = "vector"  # vector | bm25 | hybrid
    bm25_weight: float = 0.5
    rerank_enable: bool = False
    rerank_top_n: int = 10


@app.post("/api/query")
def api_query(req: QueryRequest):
    try:
        result = engine.answer(
            req.query,
            top_k=req.k,
            method=req.method,
            bm25_weight=req.bm25_weight,
            rerank_enable=req.rerank_enable,
            rerank_top_n=req.rerank_top_n,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream_query")
def api_stream_query(req: QueryRequest):
    try:
        def gen():
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
            yield "[[CTXJSON]]" + json.dumps({"contexts": ctx_docs, "metadatas": metas}) + "\n"
            prompt = engine.build_prompt(req.query, ctx_docs)
            for chunk in engine.ollama.generate_stream(prompt):
                yield chunk
        return StreamingResponse(gen(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
