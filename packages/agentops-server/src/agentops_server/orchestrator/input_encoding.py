"""Stable lexical features for input-drift detection.

These vectors deliberately describe token overlap, not semantic meaning.  SHA-256
makes the token-to-bucket mapping identical across Python processes and machines,
unlike Python's randomized built-in ``hash`` function.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

import numpy as np

LEXICAL_ENCODER_NAME = "lexical_sha256_v1"
LEXICAL_FEATURE_DIMENSIONS = 128

_TOKEN_PATTERN = re.compile(r"[^\W_]+(?:['-][^\W_]+)*", re.UNICODE)


def lexical_hash_vector(
    text: str, *, dimensions: int = LEXICAL_FEATURE_DIMENSIONS
) -> np.ndarray:
    """Return a deterministic, L2-normalized signed feature-hash vector.

    Text is Unicode-normalized and case-folded before its lexical tokens are
    hashed. Repeated tokens increase their bucket's weight. The vector is
    normalized so input length does not dominate the MMD comparison.
    """
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")

    normalized = unicodedata.normalize("NFKC", str(text)).casefold()
    vector = np.zeros(dimensions, dtype=np.float64)
    for token in _TOKEN_PATTERN.findall(normalized):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], byteorder="big") % dimensions
        sign = 1.0 if digest[8] & 1 else -1.0
        vector[bucket] += sign

    norm = float(np.linalg.norm(vector))
    if norm:
        vector /= norm
    return vector
