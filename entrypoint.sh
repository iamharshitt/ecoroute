#!/bin/bash
echo "Starting local Ollama server..."
ollama serve > /dev/null 2>&1 &

echo "Waiting 5 seconds for the AI engine to awake..."
sleep 5

echo "Starting High-Performance evaluation script..."
python main.py