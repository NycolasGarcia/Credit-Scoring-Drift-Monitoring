"""Pseudonymization of direct identifiers (LGPD art. 13 §4 style: key held separately).

The source loan id is replaced by an HMAC-SHA256 digest keyed by a secret from the
environment. Without the key the mapping cannot be recomputed or reversed.
"""

import hashlib
import hmac

import pandas as pd

KEY_MIN_LENGTH = 16
DIGEST_HEX_CHARS = 20


def _require_key(key: str) -> bytes:
    if len(key) < KEY_MIN_LENGTH:
        raise ValueError(
            "pseudonymization key missing or too short; set CDM_PSEUDONYMIZATION_KEY in .env"
        )
    return key.encode("utf-8")


def pseudonymize_ids(ids: pd.Series, key: str) -> pd.Series:
    """Return keyed digests for ``ids`` (same input and key -> same output).

    Args:
        ids: Source identifiers.
        key: Secret HMAC key (never logged).

    Returns:
        Series of hex digests named ``loan_key``.
    """
    secret = _require_key(key)

    def digest(value: object) -> str:
        mac = hmac.new(secret, str(value).encode("utf-8"), hashlib.sha256)
        return mac.hexdigest()[:DIGEST_HEX_CHARS]

    return ids.map(digest).rename("loan_key")
