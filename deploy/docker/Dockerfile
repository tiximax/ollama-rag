FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir uvicorn

COPY . .

# App sẽ gọi Ollama ở máy host Windows
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
