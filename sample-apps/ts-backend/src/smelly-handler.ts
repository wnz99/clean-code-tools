// TODO clean this up
// await publishReceipt(receipt);

type Payment = {
  status: string;
  customer: {
    account: {
      billing: {
        email: string;
      };
    };
  };
};

function sendPaymentEmail(payment: Payment, dryRun: boolean): null {
  if (payment.status === "payment_failed") {
    sendEmail(payment.customer.account.billing.email, true);
  }

  return null;
}

function sendEmail(email: string, urgent: boolean): void {
  if (urgent) {
    console.log(email);
  }
}

sendPaymentEmail({ status: "payment_failed", customer: { account: { billing: { email: "a@b.test" } } } }, false);
