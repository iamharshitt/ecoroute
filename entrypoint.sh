#!/bin/bash
set -e

echo "🚀 Booting internal Ollama Inference Engine..."
ollama serve > /dev/null 2>&1 &

for attempt in {1..60}; do
    if curl -fsS --max-time 2 http://localhost:11434/api/tags >/dev/null; then
        exec python3 main.py
    fi
    sleep 1
done

echo "Ollama startup timed out." >&2
exit 1


