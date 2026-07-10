# 🚀 EcoRoute: 3-Tier Agentic Triage Engine

## 📌 Elevator Pitch
Standard LLM wrappers burn expensive cloud tokens and introduce unnecessary latency on simple, generic user prompts. **EcoRoute** is a zero-token local triage engine that dynamically routes inference to optimize API costs and latency, featuring enterprise-grade rate limit and memory defenses.

---

## 🏆 How EcoRoute Meets the Judging Criteria

### 1. Creativity & Originality: 3-Tier Agentic Routing
We bypassed standard API wrappers to build a cost-optimizing triage system. By deploying a lightweight, local 0.5B AI (`Qwen 2.5`) directly within the container alongside a deterministic heuristic gatekeeper, EcoRoute evaluates task complexity in real-time:
* **Tier 1 (Trivial):** Local model intercepts and answers simple facts and summaries for **0 Fireworks Tokens**.
* **Tier 2 (Medium):** Tasks escalated by the local model are routed to a highly efficient 8B Fireworks model.
* **Tier 3 (Complex):** The Python gatekeeper detects heavy coding or math logic and bypasses the local model entirely, routing directly to the premium 70B Fireworks model.

### 2. Completeness: Enterprise-Grade Resilience
This container is not a fragile prototype; it is built to survive aggressive automated grading and edge cases:
* **Rate Limit Survival:** Built-in `tenacity` Exponential Backoff safely pauses and retries if the Fireworks API throws a 429 error.
* **Memory Protection:** Dynamic context truncation prevents the local server from crashing (OOM) when hit with massive text walls.
* **Grader Resilience:** Strict Schema Validation ensures outputs perfectly match the expected JSON formatting.
* **SIGTERM Defense:** Thread-locked incremental file saving guarantees partial credit is preserved even if the grading server kills the container early.
* **Asynchronous Speed:** Built with a `ThreadPoolExecutor` to process batches concurrently.

---

## 🏗️ Architecture Flow
1. `tasks.json` is loaded and passed to a multithreaded worker pool.
2. The **Heuristic Pre-Filter** scans the prompt for code/math triggers (e.g., `def`, `class`, `react`, `integral`). If found, it routes instantly to Tier 3.
3. The **Local Triage Agent** (using Few-Shot prompting) attempts to answer safe prompts locally. If it hits an edge case, it strictly outputs `ESCALATE`.
4. Tasks marked for escalation are passed to the **Fireworks API** via a dynamic fallback loop, executing Tier 2 or Tier 3 routing.
5. Results are validated against the schema, thread-locked, and incrementally appended to `results.json`.

---

## 💻 How to Run (Local Evaluation)

### 1. Build the self-contained image
*Note: The local Qwen model is baked into the image during the build phase to eliminate cold-start penalties.*
```bash
docker build --no-cache -t ecoroute-agent:latest .