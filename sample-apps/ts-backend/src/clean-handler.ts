const MAX_LOGIN_ATTEMPTS = 5;
const PAYMENT_FAILED_STATUS = "payment_failed";

interface Payment {
  readonly failedAttempts: number;
  readonly status: string;
}

function canRetryPayment(payment: Payment): boolean {
  return payment.status === PAYMENT_FAILED_STATUS && payment.failedAttempts < MAX_LOGIN_ATTEMPTS;
}

export function planPaymentRetry(payment: Payment): string {
  if (canRetryPayment(payment)) {
    return "retry";
  }

  return "skip";
}
