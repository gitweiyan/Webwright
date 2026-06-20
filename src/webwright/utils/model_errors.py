from __future__ import annotations

import re

_BILLING_PATTERNS = (
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"insufficient[_ -]?balance",
        r"quota",
        r"billing",
        r"payment required",
        r"余额",
        r"费用",
        r"\b402\b",
        r"Arrearage",
    )
)


class ModelBillingError(RuntimeError):
    """Raised when a model provider rejects a call for billing/quota reasons."""


def is_billing_error(message: str) -> bool:
    text = message or ""
    return any(pattern.search(text) for pattern in _BILLING_PATTERNS)


def raise_if_billing_error(error: BaseException) -> None:
    parts = [str(error)]
    response = getattr(error, "response", None)
    if response is not None:
        parts.append(str(getattr(response, "text", "") or ""))
    combined = "\n".join(parts)
    if is_billing_error(combined):
        raise ModelBillingError(combined) from error
