"""
Security and validation utilities.
"""

import secrets
from app.config import Config


def validate_webhook_secret(provided_token: str) -> bool:
    """
    Validate webhook secret using constant-time comparison.

    Prevents timing attacks where attacker measures comparison time
    to guess secret character by character.

    Regular comparison (==) fails fast:
    - "abc" == "xyz" fails at position 0 (fast)
    - "abc" == "ayz" fails at position 1 (slower)

    Attacker can measure response time to guess secret byte-by-byte.

    secrets.compare_digest() always compares entire string,
    preventing timing attacks.

    Args:
        provided_token: Token from X-Webhook-Token header

    Returns:
        True if valid, False otherwise
    """
    if not provided_token:
        return False

    return secrets.compare_digest(provided_token, Config.WEBHOOK_SECRET)
