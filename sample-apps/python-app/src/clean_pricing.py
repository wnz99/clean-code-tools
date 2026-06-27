MAX_RETRY_ATTEMPTS = 5
PENDING_STATUS = "pending"


def can_retry_payment(status: str, failed_attempts: int) -> bool:
    return status == PENDING_STATUS and failed_attempts < MAX_RETRY_ATTEMPTS


def calculate_total(subtotal_cents: int, tax_cents: int) -> int:
    return subtotal_cents + tax_cents
