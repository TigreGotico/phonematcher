"""The dev and test split: one key, one side, fixed by the key's hash."""
from hashlib import sha1


def is_test(key: str) -> bool:
    """True when the item with this key belongs to the test split (one in five)."""
    return int(sha1(key.encode()).hexdigest(), 16) % 5 == 0
