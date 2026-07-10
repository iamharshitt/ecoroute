FROM python:3.10-slim

# Install system dependencies and curl for Ollama
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set up the Python environment
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# CRITICAL REFACTOR: Bake the local model into the image during the build phase
# We start the server in the background, pull the model, and then shut the server down.
RUN nohup bash -c "ollama serve &" && sleep 5 && ollama pull qwen2.5:0.5b

# Make the entrypoint executable
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]