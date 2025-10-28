"""JSON helper utilities used across services."""
from __future__ import annotations

import json
from typing import Any


def to_json(data: Any, *, sort_keys: bool = False) -> str:
    """Serialise ``data`` to a compact JSON string."""
    return json.dumps(data, ensure_ascii=False, sort_keys=sort_keys)


def pretty_json(data: Any) -> str:
    """Serialise ``data`` using an indentation suited for logging/debugging."""
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


__all__ = ["to_json", "pretty_json"]
