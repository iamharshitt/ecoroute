FROM ollama/ollama:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN bash -ec 'ollama serve & server=$!; trap "kill $server 2>/dev/null || true; wait $server 2>/dev/null || true" EXIT; for attempt in {1..60}; do if curl -fsS --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1; then ollama pull qwen2.5:1.5b; exit 0; fi; sleep 1; done; echo "Ollama startup timed out" >&2; exit 1'

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
