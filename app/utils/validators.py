"""
Lightweight validation helpers for forms and JSON inputs.
"""
from __future__ import annotations

import re


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PK_PHONE_RE = re.compile(r"^03\d{9}$")


def is_valid_email(value: str | None) -> bool:
    if not value:
        return False
    return bool(_EMAIL_RE.match(value.strip()))


def is_valid_pk_phone(value: str | None) -> bool:
    if not value:
        return False
    return bool(_PK_PHONE_RE.match(value.strip()))


def is_non_empty(value: str | None) -> bool:
    return bool(value and value.strip())
