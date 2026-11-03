"""Hashes a password and checks a password against a stored hash.

UserService hashes a password when someone registers. AuthenticationService
checks it at login; that call is real even though the class diagram omits
the arrow. The hasher does not look up users or replace a stored hash.
"""

import hashlib
import hmac
import os


class PasswordHasher:
    """PBKDF2-HMAC hash with a random salt.

    The stored text includes the algorithm, the iteration count, and the salt.
    verify uses the values inside that text, so older hashes still check
    after the constructor defaults change.
    """
    def __init__(self, algorithm: str = "sha256", saltLength: int = 16, iterations: int = 310_000):
        self._algorithm = algorithm
        self._saltLength = saltLength
        self._iterations = iterations

    def hash(self, password: str) -> str:
        """Return a new salted hash. An empty password is rejected."""
        if not password:
            raise ValueError("Password cannot be empty")
        salt = os.urandom(self._saltLength)
        digest = self._derive(self._algorithm, password, salt, self._iterations)
        return f"pbkdf2_{self._algorithm}${self._iterations}${salt.hex()}${digest.hex()}"

    def verify(self, password: str, passwordHash: str) -> bool:
        """True when password matches passwordHash. A malformed hash returns False."""
        try:
            scheme, iterations, saltHex, digestHex = passwordHash.split("$")
            algorithm = scheme.removeprefix("pbkdf2_")
            candidate = self._derive(algorithm, password, bytes.fromhex(saltHex), int(iterations))
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(candidate.hex(), digestHex)

    @staticmethod
    def _derive(algorithm: str, password: str, salt: bytes, iterations: int) -> bytes:
        return hashlib.pbkdf2_hmac(algorithm, password.encode("utf-8"), salt, iterations)
