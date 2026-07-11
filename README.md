# 🌍 EcoRoute: 3-Tier AI Orchestration Engine

EcoRoute is an intelligent, cost-saving AI routing architecture built for high-throughput environments. It dynamically analyzes user prompts and routes them to the most cost-effective inference engine capable of answering them.

## 🧠 The Architecture
1. **Tier 1 (The Gatekeeper):** A Python heuristic regex engine that scans for heavy computational or coding signatures. Costs $0. 0ms latency.
2. **Tier 2 (The Local Edge):** A fully localized **Qwen2.5:1.5B** inference model baked natively into the container. It intercepts and handles simple factual questions, summarizations, and translations. Costs $0. 
3. **Tier 3 (The Cloud Fallback):** Complex logic is instantly escalated via exponential backoff to premium cloud models (DeepSeek-V4 / Llama 3.1) via the Fireworks AI API. 

## 🚀 Quick Start
EcoRoute is fully self-contained. The local edge model is baked directly into the Docker image for a 0-second cold start.

**1. Build the Engine**
```bash
docker build -t ecoroute-agent:latest .