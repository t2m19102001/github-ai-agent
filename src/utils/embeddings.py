#!/usr/bin/env python3
"""Embedding helpers."""

import hashlib
import random
from typing import List


def text_to_embedding(text: str, dimension: int = 128) -> List[float]:
    """Generate deterministic pseudo-embedding from text for demo/search fallback."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    return [rng.random() for _ in range(dimension)]
