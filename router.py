import httpx
from config import LOCAL_MODEL, OLLAMA_BASE_URL

HEAVY_SIGNALS = {
    "def ", "class ", "react", "html", "integral", 
    "math", "equation", "solve", "function", "algorithm",
    "import ", "console.log", "void ", "public class"
}

def is_complex_heuristic(prompt: str) -> bool:
    prompt_lower = prompt.lower()
    return any(sig in prompt_lower for sig in HEAVY_SIGNALS) or len(prompt.split()) > 45

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
            return response.json().get("response", "").strip()
    except (httpx.HTTPError, httpx.TimeoutException):
        pass
    
    return "ESCALATE"