import os
from app.rag_engine import RagEngine

if __name__ == "__main__":
    engine = RagEngine(persist_dir=os.path.join("data", "chroma"))
    n = engine.ingest_paths(["data/docs"]) 
    print(f"Indexed chunks: {n}")
