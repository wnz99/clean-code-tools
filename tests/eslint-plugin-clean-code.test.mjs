import { RuleTester } from "eslint";
import tsParser from "@typescript-eslint/parser";
import { describe, it } from "node:test";
import plugin from "../src/js/eslint-plugin-clean-code.mjs";

RuleTester.afterAll = () => {};
RuleTester.describe = describe;
RuleTester.it = it;

const ruleTester = new RuleTester({
  languageOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
    parser: tsParser,
  },
});

ruleTester.run("todo-format", plugin.rules["todo-format"], {
  valid: ["// TODO(BILL-412): remove legacy fallback\nconst tax = calculateTax();"],
  invalid: [
    {
      code: "// TODO remove fallback\nconst tax = calculateTax();",
      errors: [{ messageId: "invalidTodo" }],
    },
    {
      code: "// TODO(BILL-412): first ok; TODO second missing\nconst tax = calculateTax();",
      errors: [{ messageId: "invalidTodo" }],
    },
  ],
});

ruleTester.run("no-commented-out-code", plugin.rules["no-commented-out-code"], {
  valid: [
    "// Preserve provider timeout because retries are not idempotent.\nconst timeoutMs = PROVIDER_TIMEOUT_MS;",
    "// Retry failed payments; provider requires a delay.\nconst timeoutMs = PROVIDER_TIMEOUT_MS;",
  ],
  invalid: [
    {
      code: "// await publishReceipt(receipt);\nawait saveReceipt(receipt);",
      errors: [{ messageId: "commentedOutCode" }],
    },
  ],
});

ruleTester.run("no-boolean-flag-arguments", plugin.rules["no-boolean-flag-arguments"], {
  valid: [
    "sendInvoiceReminder(invoice);",
    "function sendInvoice(invoice: Invoice, options: SendInvoiceOptions): void {}",
  ],
  invalid: [
    {
      code: "sendInvoice(invoice, true);",
      errors: [{ messageId: "booleanCallArgument" }],
    },
    {
      code: "function sendInvoice(invoice: Invoice, dryRun: boolean): void {}",
      errors: [{ messageId: "booleanSelectorParameter" }],
    },
  ],
});

ruleTester.run("no-output-argument-mutation", plugin.rules["no-output-argument-mutation"], {
  valid: [
    "function addItem(items: readonly string[]): string[] { return [...items, 'new']; }",
    "function addItem(): string[] { const items: string[] = []; items.push('new'); return items; }",
    "function addItem(items: string[]): void { callbacks.forEach(() => { const items: string[] = []; items.push('new'); }); }",
  ],
  invalid: [
    {
      code: "function addItem(items: string[]): void { items.push('new'); }",
      errors: [{ messageId: "outputArgument" }],
    },
    {
      code: "function rename(user: User): void { user.name = 'Ada'; }",
      errors: [{ messageId: "outputArgument" }],
    },
    {
      code: "function addItems(items: string[]): void { values.forEach((item) => { items.push(item); }); }",
      errors: [{ messageId: "outputArgument" }],
    },
    {
      code: "function addItem(items: string[]): void { callbacks.forEach((items) => { items.push('new'); }); }",
      errors: [{ messageId: "outputArgument" }],
    },
  ],
});

ruleTester.run("no-redundant-comment", plugin.rules["no-redundant-comment"], {
  valid: ["// External provider requires retries to stay below 3.\nretryCount += 1;"],
  invalid: [
    {
      code: "// increment retry count\nretryCount += 1;",
      errors: [{ messageId: "redundantComment" }],
    },
  ],
});

ruleTester.run("no-noisy-comments", plugin.rules["no-noisy-comments"], {
  valid: [
    "// Provider rejects duplicate transfers.\nsubmitTransfer();",
    "if (ready) {\n  submitTransfer();\n}\n// provider block ended above\nnext();",
  ],
  invalid: [
    {
      code: "// ----------------\nsubmitTransfer();",
      errors: [{ messageId: "separator" }],
    },
    {
      code: "// Author: Dana\nsubmitTransfer();",
      errors: [{ messageId: "byline" }],
    },
    {
      code: "if (ready) {\n  submitTransfer();\n} // if ready",
      errors: [{ messageId: "closingBrace" }],
    },
  ],
});

ruleTester.run("no-business-policy-literals", plugin.rules["no-business-policy-literals"], {
  valid: [
    "const MAX_LOGIN_ATTEMPTS = 5;\nif (failedAttempts >= MAX_LOGIN_ATTEMPTS) lockAccount();",
    "console.log('pending');",
    "type Status = 'pending' | 'approved';",
    "type RetryCount = 3;",
    {
      code: "console.log('pending');\nmyLogger.info('pending');",
      options: [{ allowedCalls: ["myLogger.info"] }],
    },
  ],
  invalid: [
    {
      code: "if (failedAttempts >= 5) lockAccount();",
      errors: [{ messageId: "policyLiteral" }],
    },
    {
      code: "if (order.status === 'payment_failed') retryPayment();",
      errors: [{ messageId: "policyLiteral" }],
    },
    {
      code: "if (order.status === `payment_failed`) retryPayment();",
      errors: [{ messageId: "policyLiteral" }],
    },
    {
      code: "if (role === `ADMIN`) grant();",
      errors: [{ messageId: "policyLiteral" }],
    },
  ],
});

ruleTester.run("no-train-wrecks", plugin.rules["no-train-wrecks"], {
  valid: ["const city = order.shippingCity;"],
  invalid: [
    {
      code: "const city = order.customer.address.primary.city;",
      errors: [{ messageId: "trainWreck" }],
    },
  ],
});
