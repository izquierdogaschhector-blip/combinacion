"""Optional LLM narrative analysis. API keys are supplied at runtime and never written to disk."""
from __future__ import annotations
import requests


def analyze_with_ai(provider: str, api_key: str, model: str, context: dict, base_url: str = "") -> str:
    if not api_key or not api_key.strip():
        raise ValueError("Falta la API key. La IA es opcional; el resto del sistema funciona sin ella.")
    prompt = (
        "Eres un asistente de análisis de mercados. Resume los datos estructurados aportados; no inventes datos, "
        "precios, noticias ni probabilidades. Distingue observaciones de hipótesis, explica incertidumbres y "
        "presenta escenarios condicionales, riesgos e invalidación. No des una orden de compra/venta ni consejo "
        "financiero personalizado. Si faltan datos, dilo explícitamente. Responde en español.\n\nDATOS:\n"
        + __import__("json").dumps(context, ensure_ascii=False, default=str)[:24000]
    )
    provider = provider.lower().strip()
    try:
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            response = requests.post(url, params={"key": api_key.strip()}, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1200}}, timeout=(5, 60))
            data = response.json()
            if response.status_code >= 400:
                raise RuntimeError(data.get("error", {}).get("message", f"HTTP {response.status_code}"))
            return "\n".join(p.get("text", "") for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", [])).strip() or "El modelo no devolvió texto."
        if provider == "openai-compatible":
            endpoint = (base_url or "https://api.groq.com/openai/v1").rstrip("/")
            if not endpoint.endswith("/chat/completions"):
                endpoint += "/chat/completions"
            response = requests.post(endpoint, headers={"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}, json={"model": model, "messages": [{"role": "system", "content": "Analista prudente de mercados; responde en español y no inventes datos."}, {"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 1200}, timeout=(5, 60))
            data = response.json()
            if response.status_code >= 400:
                raise RuntimeError(data.get("error", {}).get("message", f"HTTP {response.status_code}"))
            return data["choices"][0]["message"]["content"]
        raise ValueError("Proveedor IA desconocido. Elige Gemini u OpenAI-compatible.")
    except requests.RequestException as exc:
        raise RuntimeError(f"No se pudo conectar con el proveedor de IA: {exc}") from exc
