import hashlib


def hash_token(raw_token: str) -> str:
    """One-way hash for storing bearer tokens (refresh tokens) safely at rest.

    Not for passwords — use argon2 (hashing.py) for those. This is deliberately
    fast: refresh tokens are high-entropy random strings, not human-guessable
    secrets, so we don't need slow/salted KDFs here.
    """
    return hashlib.sha256(raw_token.encode()).hexdigest()