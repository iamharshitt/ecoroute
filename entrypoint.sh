#!/bin/bash
set -e

echo "🚀 Booting internal Ollama Inference Engine..."
ollama serve > /dev/null 2>&1 &

while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done

echo "✅ Engine active. Native model detected!"

echo "🎯 Passing control to EcoRoute Python Orchestrator..."
python3 main.py