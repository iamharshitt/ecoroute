import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import tempfile
from time import perf_counter

import httpx
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

import config
from router import is_complex_heuristic, run_local_triage


def requires_escalation(local_text):
    return local_text.strip(" \t\r\n*_!.").upper() in {"", "ESCALATE"}


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    reraise=True,
)
async def call_cloud_with_backoff(client, model, prompt):
    return await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.1,
    )


async def process_task(task, mode, http_client, cloud_client, semaphore):
    async with semaphore:
        started = perf_counter()
        prompt = task["prompt"]
        result = {
            "id": task["id"],
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "mode": mode,
            "model": None,
            "cloud_input_tokens": 0,
            "cloud_output_tokens": 0,
        }
        if not prompt.strip():
            result.update(routed_to="Error", answer="Error: Empty prompt.")
        else:
            direct = mode == "cloud-only" or is_complex_heuristic(prompt)
            local_answer = "" if direct else await run_local_triage(http_client, prompt)
            if requires_escalation(local_answer):
                model = config.HEAVY_CLOUD_MODEL if direct else config.CHEAP_CLOUD_MODEL
                result.update(model=model, cloud_input_tokens=None, cloud_output_tokens=None)
                if cloud_client is None:
                    result.update(routed_to="Cloud (Error)", answer="Error: FIREWORKS_API_KEY is required for cloud routing.")
                else:
                    try:
                        response = await call_cloud_with_backoff(cloud_client, model, prompt)
                    except APIError as exc:
                        result.update(routed_to="Cloud (Error)", answer=f"Error: Cloud request failed ({type(exc).__name__}).")
                    else:
                        usage = response.usage
                        if usage is not None:
                            result.update(cloud_input_tokens=usage.prompt_tokens, cloud_output_tokens=usage.completion_tokens)
                        answer = response.choices[0].message.content if response.choices else None
                        if isinstance(answer, str) and answer.strip():
                            result.update(routed_to="Cloud (Tier 3)", answer=answer.strip())
                        else:
                            result.update(routed_to="Cloud (Error)", answer="Error: Empty cloud answer.")
            else:
                result.update(model=config.LOCAL_MODEL, routed_to="Local Edge (Tier 2)", answer=local_answer)
        result["latency_ms"] = round((perf_counter() - started) * 1000, 3)
        return result


def read_tasks(path):
    tasks = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(tasks, list):
        raise ValueError("Input must be a JSON array of tasks.")
    seen = set()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict) or not isinstance(task.get("prompt"), str):
            raise ValueError(f"Task {index + 1} must contain a string prompt.")
        task_id = task.get("id")
        if type(task_id) not in (str, int) or not str(task_id).strip():
            raise ValueError(f"Task {index + 1} must have a nonempty string or integer id.")
        task["id"] = str(task_id)
        if task["id"] in seen:
            raise ValueError(f"Duplicate task id: {task['id']}")
        seen.add(task["id"])
    return tasks


def save_results(path, results):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary_path = Path(stream.name)
        try:
            json.dump(results, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.close()
            os.replace(temporary_path, path)
        finally:
            stream.close()
            temporary_path.unlink(missing_ok=True)


async def async_main(input_path, output_path, mode):
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Input and output paths must differ.")
    tasks = read_tasks(input_path)
    if config.MAX_CONCURRENT_TASKS < 1:
        raise ValueError("MAX_CONCURRENT_TASKS must be at least 1.")
    if mode == "cloud-only" and not config.FIREWORKS_API_KEY:
        raise ValueError("Set FIREWORKS_API_KEY to run the cloud-only baseline.")
    cloud_client = None
    if config.FIREWORKS_API_KEY:
        cloud_client = AsyncOpenAI(
            api_key=config.FIREWORKS_API_KEY, base_url=config.FIREWORKS_BASE_URL,
            max_retries=0, timeout=30.0,
        )
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_TASKS)
    limits = httpx.Limits(max_connections=config.MAX_CONCURRENT_TASKS, max_keepalive_connections=5)
    try:
        async with httpx.AsyncClient(limits=limits, timeout=15.0) as http_client:
            results = await asyncio.gather(*(
                process_task(task, mode, http_client, cloud_client, semaphore) for task in tasks
            ))
    finally:
        if cloud_client is not None:
            await cloud_client.close()
    save_results(output_path, results)
    print(f"Wrote {len(results)} results to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Run an EcoRoute inference batch.")
    parser.add_argument("--input", type=Path, default=Path(config.INPUT_PATH))
    parser.add_argument("--output", type=Path, default=Path(config.OUTPUT_PATH))
    parser.add_argument("--mode", choices=("routed", "cloud-only"), default="routed")
    args = parser.parse_args()
    try:
        asyncio.run(async_main(args.input, args.output, args.mode))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"EcoRoute: {exc}\n")


if __name__ == "__main__":
    main()

