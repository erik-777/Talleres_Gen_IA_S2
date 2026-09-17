import json
import urllib.error
import urllib.request

OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:1b"


class LLMUnavailableError(RuntimeError):
    pass


def generate(prompt, model=DEFAULT_MODEL, temperature=0.2):
    """Send a rendered prompt to a local Ollama model and return its text response."""
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body["response"].strip()
    except urllib.error.URLError as exc:
        raise LLMUnavailableError(
            "No se pudo conectar con Ollama en "
            f"{OLLAMA_HOST}. Verifica que el servicio esté activo "
            f"('ollama serve') y que el modelo '{model}' esté disponible "
            f"('ollama pull {model}')."
        ) from exc
