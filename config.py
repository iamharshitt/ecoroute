import os

FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY", "").strip()
FIREWORKS_BASE_URL = os.getenv("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

INPUT_PATH = os.getenv("INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "/output/results.json")

# FIX 1: Switched to ungated open models to bypass the Meta Llama legal lock
_default_models = "accounts/fireworks/models/mixtral-8x7b-instruct,accounts/fireworks/models/qwen2p5-coder-32b-instruct"
ALLOWED_MODELS = [m.strip() for m in os.getenv("ALLOWED_MODELS", _default_models).split(",") if m.strip()]

CHEAP_CLOUD_MODEL = ALLOWED_MODELS[0] if ALLOWED_MODELS else "accounts/fireworks/models/mixtral-8x7b-instruct"
HEAVY_CLOUD_MODEL = ALLOWED_MODELS[-1] if ALLOWED_MODELS else "accounts/fireworks/models/qwen2p5-coder-32b-instruct"

LOCAL_MODEL = os.getenv("LOCAL_MODEL", "qwen2.5:1.5b")
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "20"))

