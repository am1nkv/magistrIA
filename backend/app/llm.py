"""Appel au modèle Mistral déployé sur Azure AI Foundry (endpoint compatible OpenAI)."""
import json
import os

from openai import OpenAI
from pydantic import ValidationError

from .prompts import SYSTEM, repair_prompt, user_prompt
from .schema import Fiche


class LLMIndisponible(Exception):
    pass


def llm_configure() -> bool:
    return bool(os.getenv("AZURE_AI_ENDPOINT") and os.getenv("AZURE_AI_KEY")) and os.getenv("MAGISTRIA_MODE") != "demo"


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
        raise LLMIndisponible("AZURE_AI_ENDPOINT / AZURE_AI_KEY non configurés (ou MAGISTRIA_MODE=demo)")
    client = _client()
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_prompt(actes_text)},
    ]
    last_error = ""
    for _ in range(2):  # 1 essai + 1 réparation
        try:
            resp = client.chat.completions.create(
                model=os.getenv("AZURE_AI_MODEL", "Mistral-Large-2411"),
                messages=messages,
                temperature=0,
                max_tokens=12000,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            raise LLMIndisponible(str(e)) from e
        content = resp.choices[0].message.content or ""
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
