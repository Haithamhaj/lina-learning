"""Small deterministic development embedding adapter behind the retrieval boundary."""

from __future__ import annotations

from hashlib import sha256
import math
import re


def deterministic_embedding(text: str, dimensions: int = 8) -> list[float]:
    """Provide a rebuildable local vector fixture, not a production model choice."""

    values = [0.0] * dimensions
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = sha256(token.encode()).digest()
        values[digest[0] % dimensions] += 1.0 if digest[1] % 2 else -1.0
    magnitude = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / magnitude for value in values]
