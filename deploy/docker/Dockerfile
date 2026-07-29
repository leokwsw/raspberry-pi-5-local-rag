FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir '.[pdf]'
CMD ["uvicorn","local_rag.api:app","--host","0.0.0.0","--port","8000"]
