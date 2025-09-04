from __future__ import annotations

import re
from typing import Iterable, List

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


