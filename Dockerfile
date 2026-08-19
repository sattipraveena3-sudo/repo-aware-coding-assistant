FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY . .
RUN pip install --no-cache-dir .
RUN mkdir -p /data
ENV REPO_ASSISTANT_WORKSPACE=/data
EXPOSE 8000
CMD ["uvicorn", "code_assistant.api:app", "--host", "0.0.0.0", "--port", "8000"]
