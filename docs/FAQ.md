# Câu hỏi thường gặp (FAQ)

Tổng hợp các câu hỏi phổ biến khi sử dụng Ollama RAG App.

Vì sao chọn ChromaDB?
- Dễ dùng, lưu trữ persistent, tích hợp tốt với Python
- Có thể chuyển sang FAISS cho truy vấn nhanh hơn (VECTOR_BACKEND=faiss)

Làm sao đổi Provider giữa Ollama và OpenAI?
- UI: chọn trong thanh điều khiển
- API: POST /api/provider { name: "ollama" | "openai" }

Reranker hoạt động ra sao?
- Nếu bật rerank_enable, hệ thống rerank contexts bằng BGE ONNX hoặc embedding simple rồi cắt top-K

Rewrite để làm gì?
- Sinh n biến thể truy vấn, hợp nhất bằng RRF trước khi rerank/generate để tăng recall

Multi-hop phù hợp khi nào?
- Khi câu hỏi cần suy luận qua nhiều bước hoặc cần tổng hợp từ nhiều tài liệu

Tôi có thể lọc theo ngôn ngữ/phiên bản?
- Có: truyền languages=[], versions=[] vào body /api/query hay /api/multihop_query

Tối ưu hiệu năng thế nào trên máy yếu?
- Dùng tinyllama, giảm OLLAMA_NUM_THREAD, giới hạn ORT_*_THREADS, tắt stream nếu không cần
