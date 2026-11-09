import re

import httpx
from config import LOCAL_MODEL, OLLAMA_BASE_URL

COMPLEX_KEYWORDS = re.compile(
    r"\b(?:react|html|integral|math|equation|solve|function|algorithm|regex)\b"
    r"|\b(?:def|class|import|void)\s+\w+|\bconsole\.log\b",
    re.IGNORECASE,
)


def is_complex_heuristic(prompt: str) -> bool:
    return bool(COMPLEX_KEYWORDS.search(prompt)) or len(prompt.split()) > 45

async def run_local_triage(client: httpx.AsyncClient, prompt: str) -> str:
    safe_prompt = prompt[:2000]
    
    system_prompt = (
        "You are a highly efficient preliminary triage agent.\n"
        "Your job is to directly answer simple tasks, and ESCALATE hard ones to a senior AI.\n\n"
        "ALLOWED TASKS (Answer these directly):\n"
        "- Basic facts (geography, history, simple definitions).\n"
        "- Text summarization or keyword extraction.\n"
        "- Grammar corrections or simple translations.\n\n"
        "FORBIDDEN TASKS (You MUST reply with exactly one word: ESCALATE):\n"
        "- Writing, explaining, or debugging ANY computer code.\n"
        "- Mathematical calculations, algebra, or physics problems.\n"
        "- Deep logic puzzles or highly creative writing."
    )
    
    try:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": LOCAL_MODEL,
                "system": system_prompt,
                "prompt": safe_prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 150}
            },
            timeout=30.0
        )
        if response.status_code == 200:
            payload = response.json()
            if isinstance(payload, dict):
                answer = payload.get("response")
                if isinstance(answer, str) and answer.strip():
                    return answer.strip()
    except (httpx.HTTPError, ValueError):
        pass
    
    return "ESCALATE"

