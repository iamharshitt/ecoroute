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

# 🔥 THE FIX: Start server, save its Process ID, pull the model, then explicitly KILL the server so the build finishes.
RUN bash -c "ollama serve & OLLAMA_PID=\$! && sleep 5 && ollama pull qwen2.5:1.5b && kill \$OLLAMA_PID && wait \$OLLAMA_PID || true"

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]