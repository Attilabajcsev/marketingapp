from __future__ import annotations

import re
from typing import Iterable, List, Optional
import os
import requests
from django.conf import settings

import numpy as np


def simple_tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def sentence_split(text: str, max_chars: int = 512) -> list[str]:
    # naive splitter by punctuation and length budget
    parts: list[str] = []
    buffer: list[str] = []
    current = 0
    for token in re.split(r"(\.|\!|\?|\n)", text):
        if token is None:
            continue
        if current + len(token) > max_chars and buffer:
            parts.append("".join(buffer).strip())
            buffer, current = [], 0
        buffer.append(token)
        current += len(token)
    if buffer:
        parts.append("".join(buffer).strip())
    return [p for p in parts if p]


def text_to_vector(text: str, vocab: dict[str, int] | None = None) -> list[float]:
    # Very simple bag-of-words hashed embedding (fixed-dim) to avoid external deps
    dim = 256
    vec = np.zeros(dim, dtype=np.float32)
    for tok in simple_tokenize(text):
        h = hash(tok) % dim
        vec[h] += 1.0
    # l2 normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec.astype(float).tolist()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def rank_by_similarity(query: str, vectors: list[tuple[int, list[float]]], texts: list[str], top_k: int = 5) -> list[int]:
    q = np.array(text_to_vector(query), dtype=np.float32)
    sims: list[tuple[int, float]] = []
    for idx, vec in vectors:
        v = np.array(vec, dtype=np.float32)
        sims.append((idx, cosine_similarity(q, v)))
    sims.sort(key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in sims[:top_k]]



def fetch_web_results(query: str, max_results: int = 3, timeout: int = 12) -> list[dict]:
    """
    Lightweight web search via Serper.dev if SERPER_API_KEY is set.
    Returns a list of { title, url, snippet }.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key or not query:
        return []
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": max_results},
            timeout=timeout,
        )
        if not resp.ok:
            return []
        data = resp.json()
        items = data.get("organic") or []
        out: list[dict] = []
        for it in items[:max_results]:
            out.append({
                "title": it.get("title") or "",
                "url": it.get("link") or "",
                "snippet": it.get("snippet") or "",
            })
        return out
    except Exception:
        return []


# --------------- OpenAI client wrapper ---------------

def _get_openai_api_key() -> str | None:
    try:
        return getattr(settings, "OPENAI_API_KEY", None)
    except Exception:
        return None


def normalize_model_name(requested: str | None) -> str:
    """
    Normalize model names to current recommended defaults.
    - Reasoning family (starts with 'o'): keep as-is (e.g., 'o4-mini')
    - Otherwise default to 'gpt-4o' for quality
    """
    name = (requested or "").strip()
    if name and name.lower().startswith("o"):
        return name
    # Default/general chat model
    return name or "gpt-4o"


def _extract_text_from_responses_payload(data: dict) -> str:
    """Best-effort extraction of assistant text from Responses API payload."""
    if not isinstance(data, dict):
        return ""
    # 1) Direct convenience field
    if isinstance(data.get("output_text"), str) and data.get("output_text"):
        return str(data.get("output_text"))
    # 2) Iterate over 'output' list variants
    output = data.get("output")
    if isinstance(output, list) and output:
        # Try output_text entries first
        for item in output:
            if isinstance(item, dict):
                if item.get("type") == "output_text" and isinstance(item.get("text"), str):
                    if item.get("text"):
                        return str(item.get("text"))
        # Then try message entries with nested content
        for item in output:
            if isinstance(item, dict) and item.get("type") == "message":
                content_list = item.get("content")
                if isinstance(content_list, list):
                    # Find text-like parts
                    texts: list[str] = []
                    for part in content_list:
                        if not isinstance(part, dict):
                            continue
                        p_type = part.get("type")
                        if p_type in {"output_text", "text"}:
                            text_val = part.get("text")
                            if isinstance(text_val, str) and text_val:
                                texts.append(text_val)
                            elif isinstance(text_val, dict) and isinstance(text_val.get("value"), str):
                                texts.append(str(text_val.get("value")))
                    if texts:
                        return "\n".join(texts)
    # 3) Choices-like fallback (compat)
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message") or {}
            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                return str(msg.get("content"))
    # 4) Generic 'content' fallback if it's plain string
    if isinstance(data.get("content"), str) and data.get("content"):
        return str(data.get("content"))
    return ""


def call_openai_responses(*, model: str, system_text: str, user_text: str, max_output_tokens: int = 512, temperature: float = 0.7, reasoning_effort: str | None = None, timeout: int = 30) -> dict:
    """
    Call OpenAI Responses API for both reasoning and non-reasoning models with a unified payload.
    Returns a dict with keys: { ok: bool, text: str, raw: dict, error: str|None }
    """
    api_key = _get_openai_api_key()
    if not api_key:
        return {"ok": False, "text": "", "raw": {}, "error": "Missing OPENAI_API_KEY"}

    is_reasoning = model.lower().startswith("o")
    url = "https://api.openai.com/v1/responses"

    payload: dict = {
        "model": model,
        "input": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        "max_output_tokens": int(max_output_tokens),
        "temperature": float(temperature),
    }
    if is_reasoning:
        payload["reasoning"] = {"effort": (reasoning_effort or "medium")}

    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
    except Exception as e:
        return {"ok": False, "text": "", "raw": {}, "error": str(e)}

    if not resp.ok:
        return {"ok": False, "text": "", "raw": {"status_code": resp.status_code, "body": resp.text}, "error": resp.text}

    data = {}
    try:
        data = resp.json()
    except Exception:
        return {"ok": False, "text": "", "raw": {}, "error": "Invalid JSON from OpenAI"}

    out_text: str = _extract_text_from_responses_payload(data)
    if not isinstance(out_text, str) or not out_text.strip():
        return {"ok": False, "text": "", "raw": data, "error": "No text in Responses payload"}
    return {"ok": True, "text": out_text, "raw": data, "error": None}


def call_openai_chat_completions(*, model: str, messages: list[dict], max_tokens: int = 512, temperature: float = 0.7, timeout: int = 30) -> dict:
    """Fallback to legacy Chat Completions for non-reasoning models."""
    api_key = _get_openai_api_key()
    if not api_key:
        return {"ok": False, "text": "", "raw": {}, "error": "Missing OPENAI_API_KEY"}
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=timeout,
        )
    except Exception as e:
        return {"ok": False, "text": "", "raw": {}, "error": str(e)}
    if not resp.ok:
        return {"ok": False, "text": "", "raw": {"status_code": resp.status_code, "body": resp.text}, "error": resp.text}
    try:
        data = resp.json()
    except Exception:
        return {"ok": False, "text": "", "raw": {}, "error": "Invalid JSON from Chat Completions"}
    text = ""
    if isinstance(data, dict):
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                msg = first.get("message") or {}
                if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                    text = str(msg.get("content"))
    if not text.strip():
        return {"ok": False, "text": "", "raw": data, "error": "No text in Chat Completions response"}
    return {"ok": True, "text": text, "raw": data, "error": None}

