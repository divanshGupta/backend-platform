from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# A single shared PasswordHasher instance. Argon2's default parameters
# (memory cost, time cost, parallelism) are already tuned to OWASP's
# current recommendations — we're not hand-tuning these unless a real
# performance/security requirement emerges later.

_hasher = PasswordHasher()

def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password for storage.

    The returned string is self-describing — it embeds the algorithm,
    version, and parameters used, so verify_password() can always
    check it correctly even if defaults change in the future.
    """
    return _hasher.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored hash.

    Returns False on mismatch rather than raising — callers (e.g. a
    login service) shouldn't need to catch argon2-specific exceptions
    just to check "did the password match."
    """
    try:
        return _hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
