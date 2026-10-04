"""Validation helpers for data supplied by API clients."""

import math
from datetime import datetime


class ValidationError(ValueError):
    """Raised when client-supplied data is missing or invalid."""


def to_number(value, field, *, integer=False, positive=False,
              minimum=None, maximum=None):
    """Convert ``value`` to an int/float, enforcing the given bounds."""
    # bool is a subclass of int, so reject it explicitly.
    if value is None or isinstance(value, bool):
        raise ValidationError(f"'{field}' must be a number")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{field}' must be a number") from None
    if not math.isfinite(number):
        raise ValidationError(f"'{field}' must be a finite number")
    if integer:
        if not number.is_integer():
            raise ValidationError(f"'{field}' must be a whole number")
        number = int(number)
    if positive and number <= 0:
        raise ValidationError(f"'{field}' must be greater than 0")
    if minimum is not None and number < minimum:
        raise ValidationError(f"'{field}' must be at least {minimum}")
    if maximum is not None and number > maximum:
        raise ValidationError(f"'{field}' must be at most {maximum}")
    return number


def _is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def require_number(data, field, **kwargs):
    """Return ``data[field]`` as a number; the field is mandatory."""
    if _is_blank(data.get(field)):
        raise ValidationError(f"'{field}' is required")
    return to_number(data[field], field, **kwargs)


def optional_number(data, field, **kwargs):
    """Return ``data[field]`` as a number, or ``None`` when absent."""
    if _is_blank(data.get(field)):
        return None
    return to_number(data[field], field, **kwargs)


def require_text(data, field, max_length=100):
    """Return ``data[field]`` as a stripped, non-empty string."""
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"'{field}' is required")
    value = value.strip()
    if len(value) > max_length:
        raise ValidationError(
            f"'{field}' must be at most {max_length} characters")
    return value


def optional_text(data, field, max_length=500):
    """Return ``data[field]`` as a stripped string, or ``None``."""
    value = data.get(field)
    if _is_blank(value):
        return None
    if not isinstance(value, str):
        raise ValidationError(f"'{field}' must be a string")
    return require_text(data, field, max_length)


def optional_date(data, field):
    """Return ``data[field]`` as an ISO ``YYYY-MM-DD`` string, or ``None``."""
    value = data.get(field)
    if _is_blank(value):
        return None
    if not isinstance(value, str):
        raise ValidationError(f"'{field}' must be a date in YYYY-MM-DD format")
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValidationError(
            f"'{field}' must be a date in YYYY-MM-DD format") from None
