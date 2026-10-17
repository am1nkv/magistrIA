"""Appel au LLM : Azure AI Foundry (Mistral) ou modèle local Ollama.

Choix du fournisseur : LLM_PROVIDER=ollama | azure (défaut : azure si configuré, sinon ollama).
"""
import json
import os

import httpx

from openai import OpenAI
from pydantic import ValidationError

from .prompts import SYSTEM, repair_prompt, user_prompt
from .schema import Fiche


class LLMIndisponible(Exception):
    pass


def _azure_configure() -> bool:
    return bool(os.getenv("AZURE_AI_ENDPOINT") and os.getenv("AZURE_AI_KEY"))


def provider() -> str:
    choix = (os.getenv("LLM_PROVIDER") or "").lower()
    if choix in ("azure", "ollama"):
        return choix
    return "azure" if _azure_configure() else "ollama"


def ollama_url() -> str:
    return os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")


def ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.2")


def ollama_modeles() -> list[str]:
    """Modèles installés localement (liste vide si Ollama ne répond pas)."""
    try:
        r = httpx.get(f"{ollama_url()}/api/tags", timeout=2)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def llm_configure() -> bool:
    if os.getenv("MAGISTRIA_MODE") == "demo":
        return False
    if provider() == "ollama":
        return any(m.split(":")[0] == ollama_model().split(":")[0] for m in ollama_modeles())
    return _azure_configure()


def nom_modele() -> str:
    return f"ollama/{ollama_model()}" if provider() == "ollama" else os.getenv("AZURE_AI_MODEL", "Mistral-Large-2411")


def _appel_ollama(messages: list[dict]) -> str:
    """API native Ollama : permet de fixer la fenêtre de contexte (num_ctx), sinon tronquée à 2-4 k tokens."""
    try:
        r = httpx.post(
            f"{ollama_url()}/api/chat",
            json={
                "model": ollama_model(),
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                    "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "16384")),
                    "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "6000")),
                },
            },
            timeout=float(os.getenv("OLLAMA_TIMEOUT", "900")),
        )
        r.raise_for_status()
        return r.json()["message"]["content"]
    except Exception as e:
        raise LLMIndisponible(f"Ollama ({ollama_url()}, modèle {ollama_model()}) : {e}") from e


def _appel_azure(messages: list[dict]) -> str:
    try:
        resp = _client().chat.completions.create(
            model=os.getenv("AZURE_AI_MODEL", "Mistral-Large-2411"),
            messages=messages,
            temperature=0,
            max_tokens=12000,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        raise LLMIndisponible(str(e)) from e
    return resp.choices[0].message.content or ""


def _client() -> OpenAI:
    key = os.environ["AZURE_AI_KEY"]
    version = os.getenv("AZURE_AI_API_VERSION")
    return OpenAI(
        base_url=os.environ["AZURE_AI_ENDPOINT"],
        api_key=key,
        default_headers={"api-key": key},
        default_query={"api-version": version} if version else None,
        timeout=300,
    )


def generer_fiche(actes_text: str) -> Fiche:
    if not llm_configure():
        raise LLMIndisponible(
            f"LLM non disponible (fournisseur « {provider()} » ; MAGISTRIA_MODE=demo ou modèle/clé absent)")
    appel = _appel_ollama if provider() == "ollama" else _appel_azure
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_prompt(actes_text)},
    ]
    last_error = ""
    for _ in range(2):  # 1 essai + 1 réparation
        content = appel(messages)
        try:
            return Fiche.model_validate(json.loads(_strip_fences(content)))
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = str(e)
            messages += [
                {"role": "assistant", "content": content},
                {"role": "user", "content": repair_prompt(last_error)},
            ]
    raise ValueError(f"Réponse du modèle invalide : {last_error[:500]}")


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    return s
