import os
import json
import asyncio
import httpx
import re
from openai import AsyncOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import config
from router import is_complex_heuristic, run_local_triage

TEMP_JSONL_PATH = config.OUTPUT_PATH.replace(".json", ".jsonl")
file_lock = asyncio.Lock()

async def write_result_stream(result_dict: dict):
    async with file_lock:
        os.makedirs(os.path.dirname(TEMP_JSONL_PATH), exist_ok=True)
        with open(TEMP_JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(result_dict) + "\n")

def compile_final_json():
    if not os.path.exists(TEMP_JSONL_PATH):
        return
    
    results = {}
    with open(TEMP_JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            results[data["id"]] = data 
            
    final_output = [results[k] for k in sorted(results.keys(), key=str)]
    with open(config.OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)
    
    os.remove(TEMP_JSONL_PATH)

def requires_escalation(local_text: str) -> bool:
    if not local_text:
        return True
    cleaned = re.sub(r'[^a-zA-Z]', '', local_text).upper()
    return "ESCALATE" in cleaned

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
    reraise=True
)
async def call_cloud_with_backoff(openai_client: AsyncOpenAI, model: str, prompt: str) -> str:
    response = await openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.1
    )
    return response.choices[0].message.content.strip()

async def process_single_task(
    task_raw: dict, 
    http_client: httpx.AsyncClient, 
    openai_client: AsyncOpenAI, 
    semaphore: asyncio.Semaphore
):
    async with semaphore:
        task_id = str(task_raw.get("id", "UNKNOWN"))
        prompt = str(task_raw.get("prompt", ""))
        
        if not prompt:
            await write_result_stream({"id": task_id, "routed_to": "Error", "answer": "Error: Empty prompt."})
            return

        if is_complex_heuristic(prompt):
            target_cloud_model = config.HEAVY_CLOUD_MODEL
            local_response = "ESCALATE"
        else:
            local_response = await run_local_triage(http_client, prompt)
            target_cloud_model = config.CHEAP_CLOUD_MODEL

        if requires_escalation(local_response):
            try:
                answer = await call_cloud_with_backoff(openai_client, target_cloud_model, prompt)
                route_taken = "Cloud (Tier 3)"
            except Exception as e:
                answer = f"Error: Remote infrastructure failure: {str(e)}"
                route_taken = "Cloud (Error)"
        else:
            answer = local_response
            route_taken = "Local Edge (Tier 2)"

        # The critical update: attaching the route_taken to the output dictionary
        await write_result_stream({"id": task_id, "routed_to": route_taken, "answer": answer})

async def async_main():
    if not os.path.exists(config.INPUT_PATH):
        print(f"❌ CRITICAL ERROR: Input file missing at {config.INPUT_PATH}. Verify Docker volume mount.")
        return

    with open(config.INPUT_PATH, "r", encoding="utf-8") as f:
        tasks_list = json.load(f)
        
    print(f"🚀 Architecture initialized. Loaded {len(tasks_list)} tasks from input folder.")

    if os.path.exists(TEMP_JSONL_PATH): os.remove(TEMP_JSONL_PATH)
    if os.path.exists(config.OUTPUT_PATH): os.remove(config.OUTPUT_PATH)

    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_TASKS)
    limits = httpx.Limits(max_connections=config.MAX_CONCURRENT_TASKS, max_keepalive_connections=5)
    timeout = httpx.Timeout(15.0)

    openai_client = AsyncOpenAI(api_key=config.FIREWORKS_API_KEY, base_url=config.FIREWORKS_BASE_URL)
    
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as http_client:
        tasks = [process_single_task(t, http_client, openai_client, semaphore) for t in tasks_list]
        await asyncio.gather(*tasks)
        
    compile_final_json()
    print(f"🎯 Execution wrapped flawlessly. Output securely saved to -> {config.OUTPUT_PATH}")

if __name__ == "__main__":
    asyncio.run(async_main())