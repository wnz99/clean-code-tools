# Clean Code Pattern Examples

Original paired TypeScript and Python examples for clean-code search, review assistance, and future lint-rule design. This corpus is organized around the named points in the book contents and Chapter 17 smell/heuristic list; it does not reproduce the book text.

Each entry is intended to be embedded as its own vector chunk.

## CC-001 Clean Code: Express Requirements Precisely

Topic: Chapter 1: Clean Code

Description: Make business rules executable and explicit instead of leaving them as vague comments or tribal knowledge.

TypeScript:

```ts
type TransferRequest = { amount: Money; from: Account; to: Account };

function validateTransfer(request: TransferRequest): void {
  if (!request.from.canDebit(request.amount)) {
    throw new InsufficientFundsError(request.from.id);
  }
}
```

Python:

```python
@dataclass(frozen=True)
class TransferRequest:
    amount: Money
    from_account: Account
    to_account: Account


def validate_transfer(request: TransferRequest) -> None:
    if not request.from_account.can_debit(request.amount):
        raise InsufficientFundsError(request.from_account.id)
```

Lint candidates: Flag comments that describe a business rule not represented by a named function, type, or test.

## CC-002 There Will Be Code: Keep Details Executable

Topic: Chapter 1: Clean Code

Description: Represent detailed requirements in code and tests, not only in planning documents.

TypeScript:

```ts
const MINIMUM_WITHDRAWAL = money("10.00");

function canWithdraw(amount: Money): boolean {
  return amount.greaterThanOrEqual(MINIMUM_WITHDRAWAL);
}
```

Python:

```python
MINIMUM_WITHDRAWAL = Money("10.00")


def can_withdraw(amount: Money) -> bool:
    return amount >= MINIMUM_WITHDRAWAL
```

Lint candidates: Flag hard-coded policy literals that are not named constants.

## CC-003 Bad Code: Stop Adding To The Mess

Topic: Chapter 1: Clean Code

Description: When code is already tangled, add a named seam before changing behavior.

TypeScript:

```ts
async function retryFailedPayment(paymentId: string): Promise<void> {
  const payment = await paymentRepository.get(paymentId);
  await retryPayment(payment);
}
```

Python:

```python
def retry_failed_payment(payment_id: str) -> None:
    payment = payment_repository.get(payment_id)
    retry_payment(payment)
```

Lint candidates: Flag large handlers that mix lookup, validation, retry policy, and notification logic.

## CC-004 Total Cost: Reduce Change Amplification

Topic: Chapter 1: Clean Code

Description: Centralize a rule so one policy change does not require edits across many modules.

TypeScript:

```ts
function isOrderEditable(order: Order): boolean {
  return order.status === "draft" || order.status === "payment_failed";
}
```

Python:

```python
def is_order_editable(order: Order) -> bool:
    return order.status in {"draft", "payment_failed"}
```

Lint candidates: Detect duplicated condition expressions across files.

## CC-005 Grand Redesign: Improve Incrementally

Topic: Chapter 1: Clean Code

Description: Prefer small replacement steps around protected behavior over a risky rewrite.

TypeScript:

```ts
function calculateInvoiceTotal(invoice: Invoice): Money {
  return invoiceTotalCalculator.calculate(invoice);
}
```

Python:

```python
def calculate_invoice_total(invoice: Invoice) -> Money:
    return invoice_total_calculator.calculate(invoice)
```

Lint candidates: No direct lint rule; require characterization tests before replacing legacy calculations.

## CC-006 Attitude: Own The Code You Touch

Topic: Chapter 1: Clean Code

Description: Leave touched code slightly clearer by naming the rule you had to understand.

TypeScript:

```ts
const requiresManualApproval = transfer.amount.isGreaterThan(DAILY_REVIEW_LIMIT);

if (requiresManualApproval) {
  queueManualApproval(transfer);
}
```

Python:

```python
requires_manual_approval = transfer.amount > DAILY_REVIEW_LIMIT

if requires_manual_approval:
    queue_manual_approval(transfer)
```

Lint candidates: Flag complex inline conditions in changed lines.

## CC-007 Primal Conundrum: Clean Is Fast

Topic: Chapter 1: Clean Code

Description: Choose a clear implementation that keeps future changes cheap instead of hiding shortcuts in rushed code.

TypeScript:

```ts
function shippingMethodFor(order: Order): ShippingMethod {
  if (order.requiresColdChain) return ShippingMethod.Refrigerated;
  return ShippingMethod.Standard;
}
```

Python:

```python
def shipping_method_for(order: Order) -> ShippingMethod:
    if order.requires_cold_chain:
        return ShippingMethod.REFRIGERATED
    return ShippingMethod.STANDARD
```

Lint candidates: Flag nested ternaries used for business policy.

## CC-008 Art Of Clean Code: Practice Refactoring

Topic: Chapter 1: Clean Code

Description: Make code easier to read through repeated small improvements, not one-time cleanup campaigns.

TypeScript:

```ts
const paidOrders = orders.filter(isPaidOrder);
const receipts = paidOrders.map(createReceipt);
```

Python:

```python
paid_orders = [order for order in orders if is_paid_order(order)]
receipts = [create_receipt(order) for order in paid_orders]
```

Lint candidates: Flag chained transformations longer than a configurable threshold.

## CC-009 What Is Clean Code: Make Intent Obvious

Topic: Chapter 1: Clean Code

Description: Clean code exposes its purpose through structure, names, and tests.

TypeScript:

```ts
function suspendDormantAccounts(accounts: Account[], now: Date): Account[] {
  return accounts.filter((account) => isDormant(account, now)).map(suspendAccount);
}
```

Python:

```python
def suspend_dormant_accounts(accounts: list[Account], now: datetime) -> list[Account]:
    return [suspend_account(account) for account in accounts if is_dormant(account, now)]
```

Lint candidates: Flag functions whose name is less specific than the domain operations inside.

## CC-010 Schools Of Thought: Prefer Team Consistency

Topic: Chapter 1: Clean Code

Description: Apply a consistent local style so readers do not have to switch conventions within the same codebase.

TypeScript:

```ts
function formatCustomerName(customer: Customer): string {
  return `${customer.givenName} ${customer.familyName}`.trim();
}
```

Python:

```python
def format_customer_name(customer: Customer) -> str:
    return f"{customer.given_name} {customer.family_name}".strip()
```

Lint candidates: Use formatter and naming rules consistently per language.

## CC-011 We Are Authors: Optimize For Readers

Topic: Chapter 1: Clean Code

Description: Code is read more often than it is written, so make the call site read naturally.

TypeScript:

```ts
if (customerCanUseCoupon(customer, coupon)) {
  applyCoupon(cart, coupon);
}
```

Python:

```python
if customer_can_use_coupon(customer, coupon):
    apply_coupon(cart, coupon)
```

Lint candidates: Flag predicate functions that do not start with a question-like prefix.

## CC-012 Boy Scout Rule: Improve Nearby Code

Topic: Chapter 1: Clean Code

Description: When editing a module, remove local clutter that directly blocks understanding.

TypeScript:

```ts
const normalizedPhoneNumber = normalizePhoneNumber(input.phoneNumber);
await customerRepository.updatePhoneNumber(customerId, normalizedPhoneNumber);
```

Python:

```python
normalized_phone_number = normalize_phone_number(payload["phone_number"])
customer_repository.update_phone_number(customer_id, normalized_phone_number)
```

Lint candidates: Flag TODO-free cleanup opportunities in changed hunks, such as newly duplicated expressions.

## CC-013 Prequel And Principles: Use Principles As Tools

Topic: Chapter 1: Clean Code

Description: Treat clean-code principles as decision aids that make code safer to change.

TypeScript:

```ts
function approveLoan(application: LoanApplication): Approval {
  validateLoanApplication(application);
  return loanPolicy.approve(application);
}
```

Python:

```python
def approve_loan(application: LoanApplication) -> Approval:
    validate_loan_application(application)
    return loan_policy.approve(application)
```

Lint candidates: No direct lint rule; use review prompts for validation, transformation, and side-effect separation.

## CC-014 Use Intention-Revealing Names

Topic: Chapter 2: Meaningful Names

Description: Name variables and functions after the domain purpose they serve.

TypeScript:

```ts
const elapsedDays = daysBetween(invoice.sentAt, now);

if (invoiceIsOverdue(invoice, elapsedDays)) {
  recordNameExample();
}
```

Python:

```python
elapsed_days = days_between(invoice.sent_at, now)

if invoice_is_overdue(invoice, elapsed_days):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-015 Avoid Disinformation

Topic: Chapter 2: Meaningful Names

Description: Do not use words that imply the wrong type, unit, or behavior.

TypeScript:

```ts
const activeUserIds = new Set(users.filter(isActive).map((user) => user.id));

if (activeUserIds.has(request.userId)) {
  recordNameExample();
}
```

Python:

```python
active_user_ids = {user.id for user in users if is_active(user)}

if request.user_id in active_user_ids:
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-016 Make Meaningful Distinctions

Topic: Chapter 2: Meaningful Names

Description: Distinguish values by their role, not by vague suffixes or numbers.

TypeScript:

```ts
const approvedAmount = applyAccountLimit(account, requestedAmount);

if (approvedAmount.isLessThan(requestedAmount)) {
  recordNameExample();
}
```

Python:

```python
approved_amount = apply_account_limit(account, requested_amount)

if approved_amount < requested_amount:
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-017 Use Pronounceable Names

Topic: Chapter 2: Meaningful Names

Description: Choose names that people can discuss out loud in reviews.

TypeScript:

```ts
const generatedAt = new Date();

if (buildExportRecord(customer, generatedAt)) {
  recordNameExample();
}
```

Python:

```python
generated_at = datetime.now(tz=UTC)

if build_export_record(customer, generated_at):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-018 Use Searchable Names

Topic: Chapter 2: Meaningful Names

Description: Give important constants and policies names that can be searched.

TypeScript:

```ts
const maxLoginAttempts = MAX_LOGIN_ATTEMPTS;

if (failedAttempts >= maxLoginAttempts) {
  recordNameExample();
}
```

Python:

```python
max_login_attempts = MAX_LOGIN_ATTEMPTS

if failed_attempts >= max_login_attempts:
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-019 Avoid Encodings

Topic: Chapter 2: Meaningful Names

Description: Do not encode implementation type into names when types can do that job.

TypeScript:

```ts
const invoiceId = request.invoiceId;

if (loadInvoice(invoiceId)) {
  recordNameExample();
}
```

Python:

```python
invoice_id = request.invoice_id

if load_invoice(invoice_id):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-020 Hungarian Notation

Topic: Chapter 2: Meaningful Names

Description: Avoid prefixes like str, int, or arr that duplicate type information.

TypeScript:

```ts
const customerEmail = customer.email;

if (sendReceipt(customerEmail)) {
  recordNameExample();
}
```

Python:

```python
customer_email = customer.email

if send_receipt(customer_email):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-021 Member Prefixes

Topic: Chapter 2: Meaningful Names

Description: Avoid noisy member prefixes when class structure already provides context.

TypeScript:

```ts
const balance = initialBalance;

if (new Wallet(balance)) {
  recordNameExample();
}
```

Python:

```python
balance = initial_balance

if Wallet(balance):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-022 Interfaces And Implementations

Topic: Chapter 2: Meaningful Names

Description: Name abstractions for the role callers need, not for mechanical implementation details.

TypeScript:

```ts
const paymentGateway = new StripePaymentGateway(client);

if (paymentGateway.capture(request)) {
  recordNameExample();
}
```

Python:

```python
payment_gateway = StripePaymentGateway(client)

if payment_gateway.capture(request):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-023 Avoid Mental Mapping

Topic: Chapter 2: Meaningful Names

Description: Do not require readers to translate terse aliases into domain terms.

TypeScript:

```ts
const paymentMethod = customer.paymentMethods[0];

if (verifyPaymentMethod(paymentMethod)) {
  recordNameExample();
}
```

Python:

```python
payment_method = customer.payment_methods[0]

if verify_payment_method(payment_method):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-024 Class Names

Topic: Chapter 2: Meaningful Names

Description: Use noun or noun-phrase class names for domain concepts.

TypeScript:

```ts
const retryPolicy = new RetryPolicy(3);

if (retryPolicy.shouldRetry(attempt)) {
  recordNameExample();
}
```

Python:

```python
retry_policy = RetryPolicy(max_attempts=3)

if retry_policy.should_retry(attempt):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-025 Method Names

Topic: Chapter 2: Meaningful Names

Description: Use verb or verb-phrase method names that describe the action or question.

TypeScript:

```ts
const isEligible = loyaltyPolicy.isEligible(customer);

if (isEligible) {
  recordNameExample();
}
```

Python:

```python
is_eligible = loyalty_policy.is_eligible(customer)

if is_eligible:
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-026 Do Not Be Cute

Topic: Chapter 2: Meaningful Names

Description: Prefer clear domain language over jokes, slang, or surprising metaphors.

TypeScript:

```ts
const deleteExpiredSessions = sessionRepository;

if (deleteExpiredSessions(sessionRepository)) {
  recordNameExample();
}
```

Python:

```python
delete_expired_sessions = session_repository

if delete_expired_sessions(session_repository):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-027 Pick One Word Per Concept

Topic: Chapter 2: Meaningful Names

Description: Use one verb for one operation across a codebase.

TypeScript:

```ts
const fetchOrder = orderRepository;

if (fetchOrder(orderId)) {
  recordNameExample();
}
```

Python:

```python
fetch_order = order_repository

if fetch_order(order_id):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-028 Do Not Pun

Topic: Chapter 2: Meaningful Names

Description: Do not reuse the same word for unrelated operations.

TypeScript:

```ts
const appendAuditEvent = auditLog;

if (appendAuditEvent(auditLog, event)) {
  recordNameExample();
}
```

Python:

```python
append_audit_event = audit_log

if append_audit_event(audit_log, event):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-029 Use Solution Domain Names

Topic: Chapter 2: Meaningful Names

Description: Use established programming terms when the concept is technical.

TypeScript:

```ts
const paymentQueue = new AsyncQueue<PaymentJob>();

if (paymentQueue.enqueue(job)) {
  recordNameExample();
}
```

Python:

```python
payment_queue = AsyncQueue[PaymentJob]()

if payment_queue.enqueue(job):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-030 Use Problem Domain Names

Topic: Chapter 2: Meaningful Names

Description: Use business vocabulary when naming business concepts.

TypeScript:

```ts
const settlementWindow = bankingCalendar.nextWindow(now);

if (settlementWindow.includes(now)) {
  recordNameExample();
}
```

Python:

```python
settlement_window = banking_calendar.next_window(now)

if settlement_window.includes(now):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-031 Add Meaningful Context

Topic: Chapter 2: Meaningful Names

Description: Add context where a value is otherwise ambiguous.

TypeScript:

```ts
const shippingAddress = parseAddress(order.shipping);

if (validateShippingAddress(shippingAddress)) {
  recordNameExample();
}
```

Python:

```python
shipping_address = parse_address(order.shipping)

if validate_shipping_address(shipping_address):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-032 Do Not Add Gratuitous Context

Topic: Chapter 2: Meaningful Names

Description: Avoid repeating module or class context in every member name.

TypeScript:

```ts
const postalCode = address.postalCode;

if (validatePostalCode(postalCode)) {
  recordNameExample();
}
```

Python:

```python
postal_code = address.postal_code

if validate_postal_code(postal_code):
    record_name_example()
```

Lint candidates: Flag vague, misleading, inconsistent, or type-encoded names according to local allowlists.

## CC-033 Small Functions

Topic: Chapter 3: Functions

Description: Keep functions short enough that the main idea is immediately visible.

TypeScript:

```ts
function canPlaceOrder(account: Account, quote: Quote): boolean {
  return hasVerifiedIdentity(account) && hasEnoughBalance(account, quote.total);
}
```

Python:

```python
def can_place_order(account: Account, quote: Quote) -> bool:
    return has_verified_identity(account) and has_enough_balance(account, quote.total)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-034 Blocks And Indenting

Topic: Chapter 3: Functions

Description: Keep blocks shallow so readers can follow the happy path without scanning a maze.

TypeScript:

```ts
function priceOrder(order: Order): Money {
  if (order.items.length === 0) throw new EmptyOrderError();
  return order.items.reduce(addItemPrice, money('0.00'));
}
```

Python:

```python
def price_order(order: Order) -> Money:
    if not order.items:
        raise EmptyOrderError()
    return sum_item_prices(order.items)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-035 Do One Thing

Topic: Chapter 3: Functions

Description: A function should combine steps at one purpose, not unrelated responsibilities.

TypeScript:

```ts
async function submitOrder(input: OrderInput): Promise<OrderReceipt> {
  const order = buildOrder(validateOrderInput(input));
  return orderGateway.submit(order);
}
```

Python:

```python
def submit_order(payload: OrderPayload) -> OrderReceipt:
    order = build_order(validate_order_payload(payload))
    return order_gateway.submit(order)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-036 Sections Within Functions

Topic: Chapter 3: Functions

Description: If a function has visible sections, extract them into named helpers.

TypeScript:

```ts
function registerCustomer(input: SignupInput): Promise<Customer> {
  const customer = createCustomer(input);
  return welcomeCustomer(customer);
}
```

Python:

```python
def register_customer(payload: SignupPayload) -> Customer:
    customer = create_customer(payload)
    return welcome_customer(customer)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-037 One Level Of Abstraction Per Function

Topic: Chapter 3: Functions

Description: Do not mix domain steps with low-level parsing or protocol details in the same function.

TypeScript:

```ts
async function onboardCustomer(form: SignupForm): Promise<Customer> {
  const customer = createCustomerProfile(form);
  await sendWelcomeEmail(customer);
  return customer;
}
```

Python:

```python
async def onboard_customer(form: SignupForm) -> Customer:
    customer = create_customer_profile(form)
    await send_welcome_email(customer)
    return customer
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-038 Stepdown Rule

Topic: Chapter 3: Functions

Description: Order functions so high-level behavior leads readers down into details.

TypeScript:

```ts
async function closeAccount(id: string): Promise<void> {
  const account = await loadClosableAccount(id);
  await archiveAccount(account);
}

function loadClosableAccount(id: string): Promise<Account> {
  return accountRepository.getClosable(id);
}
```

Python:

```python
def close_account(account_id: str) -> None:
    account = load_closable_account(account_id)
    archive_account(account)

def load_closable_account(account_id: str) -> Account:
    return account_repository.get_closable(account_id)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-039 Switch Statements

Topic: Chapter 3: Functions

Description: Move repeated branching behind one named polymorphic or dispatch boundary.

TypeScript:

```ts
const handlers: Record<OrderType, (order: Order) => Promise<void>> = {
  market: submitMarketOrder,
  limit: submitLimitOrder,
};

await handlers[order.type](order);
```

Python:

```python
handlers: dict[OrderType, Callable[[Order], None]] = {
    OrderType.MARKET: submit_market_order,
    OrderType.LIMIT: submit_limit_order,
}

handlers[order.type](order)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-040 Use Descriptive Function Names

Topic: Chapter 3: Functions

Description: Make function names explain the rule at the call site.

TypeScript:

```ts
if (isEligibleForFreeShipping(cart, customer)) {
  applyFreeShipping(cart);
}
```

Python:

```python
if is_eligible_for_free_shipping(cart, customer):
    apply_free_shipping(cart)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-041 Function Arguments

Topic: Chapter 3: Functions

Description: Keep argument lists short and cohesive.

TypeScript:

```ts
function scheduleDelivery(orderId: string, window: DeliveryWindow): Promise<void> {
  return deliveryScheduler.schedule(orderId, window);
}
```

Python:

```python
def schedule_delivery(order_id: str, window: DeliveryWindow) -> None:
    delivery_scheduler.schedule(order_id, window)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-042 Common Monadic Forms

Topic: Chapter 3: Functions

Description: Use one-argument functions for clear transformations or questions.

TypeScript:

```ts
const normalizedEmail = normalizeEmail(input.email);
```

Python:

```python
normalized_email = normalize_email(payload['email'])
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-043 Flag Arguments

Topic: Chapter 3: Functions

Description: Replace boolean mode switches with separate intention-revealing functions.

TypeScript:

```ts
sendInvoiceEmail(invoice);
sendInvoiceReminder(invoice);
```

Python:

```python
send_invoice_email(invoice)
send_invoice_reminder(invoice)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-044 Dyadic Functions

Topic: Chapter 3: Functions

Description: Use two-argument functions only when the relationship is natural and clear.

TypeScript:

```ts
const distance = distanceBetween(origin, destination);
```

Python:

```python
distance = distance_between(origin, destination)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-045 Triads

Topic: Chapter 3: Functions

Description: Wrap three related values in a named object when they form a concept.

TypeScript:

```ts
const window = new DeliveryWindow(startAt, endAt, timezone);
scheduleDelivery(orderId, window);
```

Python:

```python
window = DeliveryWindow(starts_at, ends_at, timezone)
schedule_delivery(order_id, window)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-046 Argument Objects

Topic: Chapter 3: Functions

Description: Name cohesive parameter groups as value objects.

TypeScript:

```ts
type DateRange = { startsAt: Date; endsAt: Date };
loadStatements(accountId, range);
```

Python:

```python
@dataclass(frozen=True)
class DateRange:
    starts_at: datetime
    ends_at: datetime

load_statements(account_id, range)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-047 Argument Lists

Topic: Chapter 3: Functions

Description: Use variadic arguments only for homogeneous values with a clear meaning.

TypeScript:

```ts
function combineTags(...tags: string[]): string[] {
  return [...new Set(tags.map(normalizeTag))];
}
```

Python:

```python
def combine_tags(*tags: str) -> list[str]:
    return list({normalize_tag(tag) for tag in tags})
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-048 Verbs And Keywords

Topic: Chapter 3: Functions

Description: Choose names that pair clearly with their arguments.

TypeScript:

```ts
assertAccountCanTransfer(account, amount);
```

Python:

```python
assert_account_can_transfer(account, amount)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-049 Have No Side Effects

Topic: Chapter 3: Functions

Description: Do not hide writes or I/O inside functions that look like pure calculations.

TypeScript:

```ts
function calculateReceipt(order: Order): Receipt {
  return Receipt.from(order);
}
```

Python:

```python
def calculate_receipt(order: Order) -> Receipt:
    return Receipt.from_order(order)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-050 Output Arguments

Topic: Chapter 3: Functions

Description: Return new values instead of mutating arguments for hidden output.

TypeScript:

```ts
const enrichedOrder = addTaxDetails(order, taxRate);
```

Python:

```python
enriched_order = add_tax_details(order, tax_rate)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-051 Command Query Separation

Topic: Chapter 3: Functions

Description: Ask questions and perform commands in separate calls.

TypeScript:

```ts
if (!cartHasItem(cart, sku)) {
  addItemToCart(cart, sku);
}
```

Python:

```python
if not cart_has_item(cart, sku):
    add_item_to_cart(cart, sku)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-052 Prefer Exceptions To Returning Error Codes

Topic: Chapter 3: Functions

Description: Use explicit failures so callers cannot ignore errors accidentally.

TypeScript:

```ts
if (!invoice) {
  throw new InvoiceNotFoundError(invoiceId);
}
return invoice;
```

Python:

```python
if invoice is None:
    raise InvoiceNotFoundError(invoice_id)
return invoice
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-053 Extract Try/Catch Blocks

Topic: Chapter 3: Functions

Description: Keep error translation separate from the main behavior.

TypeScript:

```ts
try {
  return await loadCustomerView(id);
} catch (error) {
  throw mapCustomerError(error, id);
}
```

Python:

```python
try:
    return load_customer_view(customer_id)
except RepositoryError as error:
    raise map_customer_error(error, customer_id) from error
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-054 Error Handling Is One Thing

Topic: Chapter 3: Functions

Description: Do not mix fallback, logging, and business decisions in the same catch block.

TypeScript:

```ts
async function readSettings(): Promise<Settings> {
  try {
    return await settingsStore.read();
  } catch (error) {
    return defaultSettingsFor(error);
  }
}
```

Python:

```python
def read_settings() -> Settings:
    try:
        return settings_store.read()
    except SettingsStoreError as error:
        return default_settings_for(error)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-055 Error Dependency Magnet

Topic: Chapter 3: Functions

Description: Keep shared error definitions small so unrelated modules do not depend on one bloated error file.

TypeScript:

```ts
export class PaymentDeclinedError extends Error {
  constructor(readonly paymentId: string) {
    super(`Payment declined: ${paymentId}`);
  }
}
```

Python:

```python
class PaymentDeclinedError(Exception):
    def __init__(self, payment_id: str) -> None:
        super().__init__(f'Payment declined: {payment_id}')
        self.payment_id = payment_id
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-056 Do Not Repeat Yourself

Topic: Chapter 3: Functions

Description: Extract repeated knowledge into a single named rule.

TypeScript:

```ts
function isPasswordExpired(changedAt: Date, now: Date): boolean {
  return daysBetween(changedAt, now) > PASSWORD_EXPIRY_DAYS;
}
```

Python:

```python
def is_password_expired(changed_at: datetime, now: datetime) -> bool:
    return days_between(changed_at, now) > PASSWORD_EXPIRY_DAYS
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-057 Structured Programming

Topic: Chapter 3: Functions

Description: Use simple structured control flow before reaching for jumps, flags, or tangled exits.

TypeScript:

```ts
for (const item of order.items) {
  validateOrderItem(item);
}
```

Python:

```python
for item in order.items:
    validate_order_item(item)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-058 How To Write Functions Like This

Topic: Chapter 3: Functions

Description: Refine functions through repeated extraction, renaming, and testing.

TypeScript:

```ts
const order = buildOrder(input);
validateOrder(order);
await submitOrder(order);
```

Python:

```python
order = build_order(payload)
validate_order(order)
submit_order(order)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-059 SetupTeardownIncluder

Topic: Chapter 3: Functions

Description: Separate setup, execution, and teardown so each phase is understandable.

TypeScript:

```ts
const server = await startTestServer();
try {
  await runContractTests(server.url);
} finally {
  await server.stop();
}
```

Python:

```python
with start_test_server() as server:
    run_contract_tests(server.url)
```

Lint candidates: Flag excessive length, argument count, flag arguments, hidden mutation, and mixed abstraction levels.

## CC-060 Comments Do Not Make Up For Bad Code

Topic: Chapter 4: Comments

Description: Improve the code structure before adding a comment to explain confusing logic.

TypeScript:

```ts
const isPriorityRefund = refund.amount.greaterThan(PRIORITY_REFUND_AMOUNT);
if (isPriorityRefund) escalateRefund(refund);
```

Python:

```python
is_priority_refund = refund.amount > PRIORITY_REFUND_AMOUNT
if is_priority_refund:
    escalate_refund(refund)
```

Lint candidates: Flag comments before complex boolean expressions.

## CC-061 Explain Yourself In Code

Topic: Chapter 4: Comments

Description: Use named helpers and variables to explain intent directly in executable code.

TypeScript:

```ts
if (isWithinGracePeriod(invoice, now)) skipLateFee(invoice);
```

Python:

```python
if is_within_grace_period(invoice, now):
    skip_late_fee(invoice)
```

Lint candidates: Suggest extracting named predicates for complex conditions.

## CC-062 Good Comments

Topic: Chapter 4: Comments

Description: Reserve comments for non-obvious context that code cannot express well.

TypeScript:

```ts
// Provider clocks can drift, so submit one minute behind our observed time.
const submittedAt = subtractMinutes(now, 1);
```

Python:

```python
# Provider clocks can drift, so submit one minute behind our observed time.
submitted_at = now - timedelta(minutes=1)
```

Lint candidates: Allow comments that explain why, constraints, or external behavior.

## CC-063 Legal Comments

Topic: Chapter 4: Comments

Description: Keep required legal notices brief and point to the canonical license when possible.

TypeScript:

```ts
// SPDX-License-Identifier: MIT
export function parseAmount(value: string): Money {
  return Money.parse(value);
}
```

Python:

```python
# SPDX-License-Identifier: MIT
def parse_amount(value: str) -> Money:
    return Money.parse(value)
```

Lint candidates: Enforce SPDX headers instead of long pasted licenses.

## CC-064 Informative Comments

Topic: Chapter 4: Comments

Description: Use a short comment when it names a format or convention that is not obvious locally.

TypeScript:

```ts
// External report format: YYYYMMDD-accountId.csv
const reportName = `${formatDate(day)}-${accountId}.csv`;
```

Python:

```python
# External report format: YYYYMMDD-account_id.csv
report_name = f'{format_date(day)}-{account_id}.csv'
```

Lint candidates: Allow comments documenting external wire/file formats.

## CC-065 Explanation Of Intent

Topic: Chapter 4: Comments

Description: Explain why an unusual choice is intentional.

TypeScript:

```ts
// Prefer a stale cached quote over blocking checkout during provider outages.
return cachedQuote ?? await quoteProvider.fetch(pair);
```

Python:

```python
# Prefer a stale cached quote over blocking checkout during provider outages.
return cached_quote or quote_provider.fetch(pair)
```

Lint candidates: Allow comments containing tradeoff terms such as prefer, because, or during.

## CC-066 Clarification Comments

Topic: Chapter 4: Comments

Description: Clarify awkward third-party behavior at the boundary, not throughout the codebase.

TypeScript:

```ts
// The SDK returns cents as a string.
const amount = Money.fromCents(Number(response.amount));
```

Python:

```python
# The SDK returns cents as a string.
amount = Money.from_cents(int(response.amount))
```

Lint candidates: Flag clarification comments far from third-party calls.

## CC-067 Warning Of Consequences

Topic: Chapter 4: Comments

Description: Use warnings sparingly for traps that tests cannot make obvious.

TypeScript:

```ts
// Do not parallelize; the provider rejects concurrent captures for one invoice.
for (const capture of captures) await capturePayment(capture);
```

Python:

```python
# Do not parallelize; the provider rejects concurrent captures for one invoice.
for capture in captures:
    capture_payment(capture)
```

Lint candidates: Allow warning comments near concurrency or provider constraints.

## CC-068 TODO Comments

Topic: Chapter 4: Comments

Description: Make TODOs actionable, owned, and searchable.

TypeScript:

```ts
// TODO(BILL-412): remove legacy tax fallback after the July migration.
const tax = legacyTaxFallback(order);
```

Python:

```python
# TODO(BILL-412): remove legacy tax fallback after the July migration.
tax = legacy_tax_fallback(order)
```

Lint candidates: Require issue IDs or owners in TODO comments.

## CC-069 Amplification Comments

Topic: Chapter 4: Comments

Description: Highlight a small detail only when missing it causes real damage.

TypeScript:

```ts
// This comparison must stay case-sensitive; coupon codes are customer-visible.
return inputCode === storedCode;
```

Python:

```python
# This comparison must stay case-sensitive; coupon codes are customer-visible.
return input_code == stored_code
```

Lint candidates: Allow comments that contain must/critical and a reason.

## CC-070 Javadocs In Public APIs

Topic: Chapter 4: Comments

Description: Document public APIs when callers cannot infer contract, units, or failure modes.

TypeScript:

```ts
/** Captures a payment and throws PaymentDeclinedError when the provider rejects it. */
export function capturePayment(request: PaymentRequest): Promise<Receipt> {
  return gateway.capture(request);
}
```

Python:

```python
def capture_payment(request: PaymentRequest) -> Receipt:
    """Capture a payment or raise PaymentDeclinedError when rejected."""
    return gateway.capture(request)
```

Lint candidates: Require docs on exported APIs in library packages only.

## CC-071 Bad Comments

Topic: Chapter 4: Comments

Description: Remove comments that duplicate, mislead, or compensate for unclear code.

TypeScript:

```ts
const retryDelayMs = retryPolicy.delayFor(attempt);
```

Python:

```python
retry_delay_ms = retry_policy.delay_for(attempt)
```

Lint candidates: Flag comments that restate adjacent identifiers.

## CC-072 Mumbling Comments

Topic: Chapter 4: Comments

Description: Do not leave vague notes that force readers to guess their meaning.

TypeScript:

```ts
const normalizedSku = normalizeSku(input.sku);
```

Python:

```python
normalized_sku = normalize_sku(payload['sku'])
```

Lint candidates: Flag comments containing unclear words such as hack, maybe, stuff, or magic without issue links.

## CC-073 Redundant Comments

Topic: Chapter 4: Comments

Description: Delete comments that repeat exactly what the code says.

TypeScript:

```ts
const total = subtotal.plus(tax);
```

Python:

```python
total = subtotal + tax
```

Lint candidates: Flag comments whose tokens overlap heavily with the following line.

## CC-074 Misleading Comments

Topic: Chapter 4: Comments

Description: Prefer no comment over a stale or incorrect explanation.

TypeScript:

```ts
const timeoutMs = settings.paymentTimeoutMs;
```

Python:

```python
timeout_ms = settings.payment_timeout_ms
```

Lint candidates: Flag comments mentioning values that differ from nearby literals or constants.

## CC-075 Mandated Comments

Topic: Chapter 4: Comments

Description: Do not require boilerplate comments for every variable or private function.

TypeScript:

```ts
function normalizeSku(sku: string): string {
  return sku.trim().toUpperCase();
}
```

Python:

```python
def normalize_sku(sku: str) -> str:
    return sku.strip().upper()
```

Lint candidates: Disable rules requiring docs for every private member.

## CC-076 Journal Comments

Topic: Chapter 4: Comments

Description: Use version control for history instead of log-style comments in files.

TypeScript:

```ts
const receipt = await paymentGateway.capture(request);
```

Python:

```python
receipt = payment_gateway.capture(request)
```

Lint candidates: Flag dated change-log comments in source files.

## CC-077 Noise Comments

Topic: Chapter 4: Comments

Description: Remove filler comments that add no decision, warning, or contract.

TypeScript:

```ts
return orderRepository.findById(orderId);
```

Python:

```python
return order_repository.find_by_id(order_id)
```

Lint candidates: Flag comments matching boilerplate patterns like default constructor.

## CC-078 Scary Noise

Topic: Chapter 4: Comments

Description: Avoid copied documentation blocks that hide the useful code.

TypeScript:

```ts
export class CustomerRepository {
  findById(id: string): Promise<Customer | null> {
    return db.customers.find(id);
  }
}
```

Python:

```python
class CustomerRepository:
    def find_by_id(self, customer_id: str) -> Customer | None:
        return db.customers.find(customer_id)
```

Lint candidates: Flag repeated doc comments with only identifier substitutions.

## CC-079 Use A Function Or Variable Instead Of A Comment

Topic: Chapter 4: Comments

Description: Replace explanatory comments with named predicates when possible.

TypeScript:

```ts
const isEligibleForRenewal = subscription.active && !subscription.cancelled;
```

Python:

```python
is_eligible_for_renewal = subscription.active and not subscription.cancelled
```

Lint candidates: Suggest extracted variables for comments before conditions.

## CC-080 Position Markers

Topic: Chapter 4: Comments

Description: Do not use banner comments to compensate for oversized files.

TypeScript:

```ts
export function parseInvoice(input: unknown): Invoice {
  return invoiceSchema.parse(input);
}
```

Python:

```python
def parse_invoice(payload: object) -> Invoice:
    return invoice_schema.parse(payload)
```

Lint candidates: Flag repeated separator comments.

## CC-081 Closing Brace Comments

Topic: Chapter 4: Comments

Description: Keep blocks short enough that closing comments are unnecessary.

TypeScript:

```ts
if (canArchive(order)) {
  archive(order);
}
```

Python:

```python
if can_archive(order):
    archive(order)
```

Lint candidates: Flag comments after closing braces or dedents.

## CC-082 Attributions And Bylines

Topic: Chapter 4: Comments

Description: Keep authorship in version control, not source comments.

TypeScript:

```ts
export function applyDiscount(cart: Cart, discount: Discount): Cart {
  return cart.apply(discount);
}
```

Python:

```python
def apply_discount(cart: Cart, discount: Discount) -> Cart:
    return cart.apply(discount)
```

Lint candidates: Flag author/by/date comments outside license headers.

## CC-083 Commented-Out Code

Topic: Chapter 4: Comments

Description: Remove dead code instead of leaving it commented beside live code.

TypeScript:

```ts
const receipt = await paymentGateway.capture(request);
await receiptRepository.save(receipt);
```

Python:

```python
receipt = payment_gateway.capture(request)
receipt_repository.save(receipt)
```

Lint candidates: Flag comment blocks containing code syntax.

## CC-084 HTML Comments

Topic: Chapter 4: Comments

Description: Avoid HTML markup in source comments unless generating external docs requires it.

TypeScript:

```ts
/** Returns the account balance in the requested currency. */
export function balanceFor(account: Account, currency: string): Money {
  return account.balance.convertTo(currency);
}
```

Python:

```python
def balance_for(account: Account, currency: str) -> Money:
    """Return the account balance in the requested currency."""
    return account.balance.convert_to(currency)
```

Lint candidates: Flag HTML tags in comments outside generated docs.

## CC-085 Nonlocal Information

Topic: Chapter 4: Comments

Description: Do not document distant systems in a local implementation comment.

TypeScript:

```ts
const timeoutMs = config.paymentGateway.timeoutMs;
await paymentGateway.capture(request, { timeoutMs });
```

Python:

```python
timeout_seconds = config.payment_gateway.timeout_seconds
payment_gateway.capture(request, timeout=timeout_seconds)
```

Lint candidates: Flag comments naming services not referenced nearby.

## CC-086 Too Much Information

Topic: Chapter 4: Comments

Description: Keep comments focused on the local decision, not broad historical essays.

TypeScript:

```ts
// Preserve provider order because reconciliation compares row numbers.
return rows;
```

Python:

```python
# Preserve provider order because reconciliation compares row numbers.
return rows
```

Lint candidates: Warn on long comments in function bodies.

## CC-087 Inobvious Connection

Topic: Chapter 4: Comments

Description: A comment and the code it explains should be directly connected.

TypeScript:

```ts
const retryAfter = parseRetryAfter(response.headers);
```

Python:

```python
retry_after = parse_retry_after(response.headers)
```

Lint candidates: Flag comments separated from the referenced symbol by many lines.

## CC-088 Function Headers

Topic: Chapter 4: Comments

Description: Prefer a well-named small function over a private function header comment.

TypeScript:

```ts
function calculateRefundAmount(order: Order): Money {
  return order.paidAmount.minus(order.consumedValue);
}
```

Python:

```python
def calculate_refund_amount(order: Order) -> Money:
    return order.paid_amount - order.consumed_value
```

Lint candidates: Flag docblocks on short private functions when the name already says the same thing.

## CC-089 Javadocs In Nonpublic Code

Topic: Chapter 4: Comments

Description: Avoid heavy API documentation for private implementation details.

TypeScript:

```ts
function normalizeCountryCode(countryCode: string): string {
  return countryCode.trim().toUpperCase();
}
```

Python:

```python
def normalize_country_code(country_code: str) -> str:
    return country_code.strip().upper()
```

Lint candidates: Warn on verbose docs for private helpers.

## CC-090 Purpose Of Formatting

Topic: Chapter 5: Formatting

Description: Format code to communicate structure consistently.

TypeScript:

```ts
const order = buildOrder(input);
const receipt = await submitOrder(order);
```

Python:

```python
order = build_order(payload)
receipt = submit_order(order)
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-091 Vertical Formatting

Topic: Chapter 5: Formatting

Description: Use vertical structure to reveal the story of a file.

TypeScript:

```ts
const quote = priceOrder(order);

await quoteRepository.save(quote);
```

Python:

```python
quote = price_order(order)

quote_repository.save(quote)
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-092 Newspaper Metaphor

Topic: Chapter 5: Formatting

Description: Put high-level concepts first, then lower-level details.

TypeScript:

```ts
export async function checkout(cart: Cart): Promise<Receipt> {
  return submitPricedOrder(priceCart(cart));
}
```

Python:

```python
def checkout(cart: Cart) -> Receipt:
    return submit_priced_order(price_cart(cart))
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-093 Vertical Openness Between Concepts

Topic: Chapter 5: Formatting

Description: Separate distinct ideas with blank lines.

TypeScript:

```ts
const order = buildOrder(input);
const quote = priceOrder(order);

await publishQuoteCreated(quote);
```

Python:

```python
order = build_order(payload)
quote = price_order(order)

publish_quote_created(quote)
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-094 Vertical Density

Topic: Chapter 5: Formatting

Description: Keep tightly related lines adjacent.

TypeScript:

```ts
const amount = parseAmount(input.amount);
const currency = parseCurrency(input.currency);
const money = new Money(amount, currency);
```

Python:

```python
amount = parse_amount(payload['amount'])
currency = parse_currency(payload['currency'])
money = Money(amount, currency)
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-095 Vertical Distance

Topic: Chapter 5: Formatting

Description: Keep declarations and helpers near the code that uses them.

TypeScript:

```ts
const RETRYABLE_CODES = new Set(['timeout']);
function shouldRetry(error: ProviderError): boolean {
  return RETRYABLE_CODES.has(error.code);
}
```

Python:

```python
RETRYABLE_CODES = {'timeout'}

def should_retry(error: ProviderError) -> bool:
    return error.code in RETRYABLE_CODES
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-096 Vertical Ordering

Topic: Chapter 5: Formatting

Description: Order code from public/high-level behavior to private details.

TypeScript:

```ts
export function createReceipt(order: Order): Receipt {
  return buildReceipt(order);
}

function buildReceipt(order: Order): Receipt {
  return Receipt.from(order);
}
```

Python:

```python
def create_receipt(order: Order) -> Receipt:
    return build_receipt(order)

def build_receipt(order: Order) -> Receipt:
    return Receipt.from_order(order)
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-097 Horizontal Formatting

Topic: Chapter 5: Formatting

Description: Keep lines short and expressions readable.

TypeScript:

```ts
const total = subtotal.plus(tax).minus(discount);
```

Python:

```python
total = subtotal + tax - discount
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-098 Horizontal Openness And Density

Topic: Chapter 5: Formatting

Description: Use spaces to separate operators and arguments in conventional ways.

TypeScript:

```ts
const fee = amount.multiply(rate).plus(minimumFee);
```

Python:

```python
fee = amount * rate + minimum_fee
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-099 Horizontal Alignment

Topic: Chapter 5: Formatting

Description: Avoid alignment that emphasizes columns over relationships.

TypeScript:

```ts
const id = customer.id;
const email = customer.email;
```

Python:

```python
customer_id = customer.id
email = customer.email
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-100 Indentation

Topic: Chapter 5: Formatting

Description: Indent blocks so nesting and ownership are obvious.

TypeScript:

```ts
if (isValid(order)) {
  submit(order);
}
```

Python:

```python
if is_valid(order):
    submit(order)
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-101 Dummy Scopes

Topic: Chapter 5: Formatting

Description: Avoid empty or dummy scopes that obscure control flow.

TypeScript:

```ts
while (queue.hasNext()) {
  process(queue.next());
}
```

Python:

```python
while queue.has_next():
    process(queue.next())
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-102 Team Rules

Topic: Chapter 5: Formatting

Description: Follow shared formatter and style rules instead of personal preference.

TypeScript:

```ts
export const formatterConfig = { printWidth: 100 };
```

Python:

```python
LINE_LENGTH = 100
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-103 Formatting Rules

Topic: Chapter 5: Formatting

Description: Let automated formatting handle mechanical layout decisions.

TypeScript:

```ts
const formatted = formatter.format(sourceText);
```

Python:

```python
formatted = formatter.format(source_text)
```

Lint candidates: Enforce with formatter and style lint rules where possible.

## CC-104 Data Abstraction

Topic: Chapter 6: Objects and Data Structures

Description: Expose operations that preserve invariants instead of raw representation.

TypeScript:

```ts
wallet.canCover(amount)
```

Python:

```python
wallet.can_cover(amount)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-105 Data Object Anti-Symmetry

Topic: Chapter 6: Objects and Data Structures

Description: Choose objects for behavior and data structures for transparent data transfer.

TypeScript:

```ts
const total = order.total();
```

Python:

```python
total = order.total()
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-106 Law Of Demeter

Topic: Chapter 6: Objects and Data Structures

Description: Talk to immediate collaborators instead of navigating through object internals.

TypeScript:

```ts
const city = order.shippingCity();
```

Python:

```python
city = order.shipping_city()
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-107 Train Wrecks

Topic: Chapter 6: Objects and Data Structures

Description: Replace long chains with a named method on the owning concept.

TypeScript:

```ts
const owner = project.ownerEmail();
```

Python:

```python
owner = project.owner_email()
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-108 Hybrids

Topic: Chapter 6: Objects and Data Structures

Description: Avoid types that expose raw data while also pretending to protect behavior.

TypeScript:

```ts
const status = invoice.currentStatus();
```

Python:

```python
status = invoice.current_status()
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-109 Hiding Structure

Topic: Chapter 6: Objects and Data Structures

Description: Ask an object to do work rather than exposing its nested structure.

TypeScript:

```ts
order.scheduleShipment(carrier);
```

Python:

```python
order.schedule_shipment(carrier)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-110 Data Transfer Objects

Topic: Chapter 6: Objects and Data Structures

Description: Use DTOs as simple boundary shapes without domain behavior.

TypeScript:

```ts
type CreateUserRequest = { email: string; name: string };
```

Python:

```python
class CreateUserRequest(TypedDict):
    email: str
    name: str
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-111 Active Record

Topic: Chapter 6: Objects and Data Structures

Description: Keep persistence records separate from richer domain policy when behavior grows.

TypeScript:

```ts
const customer = Customer.fromRecord(record);
```

Python:

```python
customer = Customer.from_record(record)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-112 Use Exceptions Rather Than Return Codes

Topic: Chapter 7: Error Handling

Description: Represent failure explicitly so callers cannot ignore it.

TypeScript:

```ts
if (!user) throw new UserNotFoundError(userId);
```

Python:

```python
if user is None:
    raise UserNotFoundError(user_id)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-113 Write Try Catch Finally First

Topic: Chapter 7: Error Handling

Description: Define the failure boundary before filling in risky work.

TypeScript:

```ts
try {
  await importFile(file);
} finally {
  await file.close();
}
```

Python:

```python
with open_import_file(path) as file:
    import_file(file)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-114 Use Unchecked Exceptions

Topic: Chapter 7: Error Handling

Description: Keep ordinary call chains free from plumbing error codes.

TypeScript:

```ts
throw new PaymentDeclinedError(paymentId);
```

Python:

```python
raise PaymentDeclinedError(payment_id)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-115 Provide Context With Exceptions

Topic: Chapter 7: Error Handling

Description: Attach useful identifiers and operation context to failures.

TypeScript:

```ts
throw new QuoteLoadError(pair, { cause: error });
```

Python:

```python
raise QuoteLoadError(pair) from error
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-116 Define Exception Classes By Caller Needs

Topic: Chapter 7: Error Handling

Description: Group errors by what callers can do about them.

TypeScript:

```ts
catch (error) {
  if (error instanceof RetryablePaymentError) retry();
}
```

Python:

```python
except RetryablePaymentError:
    retry()
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-117 Define The Normal Flow

Topic: Chapter 7: Error Handling

Description: Use a normal object or policy when an expected case is not exceptional.

TypeScript:

```ts
const plan = customer.plan ?? FreePlan.default();
```

Python:

```python
plan = customer.plan or FreePlan.default()
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-118 Do Not Return Null

Topic: Chapter 7: Error Handling

Description: Return empty collections or explicit option types instead of null surprises.

TypeScript:

```ts
return ordersByCustomer.get(customerId) ?? [];
```

Python:

```python
return orders_by_customer.get(customer_id, [])
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-119 Do Not Pass Null

Topic: Chapter 7: Error Handling

Description: Require real values at boundaries and fail early for absent dependencies.

TypeScript:

```ts
submitOrder(requireCustomer(customer));
```

Python:

```python
submit_order(require_customer(customer))
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-120 Using Third-Party Code

Topic: Chapter 8: Boundaries

Description: Wrap third-party APIs behind app-shaped adapters.

TypeScript:

```ts
emailSender.sendWelcomeEmail(customer);
```

Python:

```python
email_sender.send_welcome_email(customer)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-121 Exploring And Learning Boundaries

Topic: Chapter 8: Boundaries

Description: Write small experiments to learn an external API before embedding it deeply.

TypeScript:

```ts
expect(parseProviderDate(sample)).toEqual(expectedDate);
```

Python:

```python
assert parse_provider_date(sample) == expected_date
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-122 Learning log4j

Topic: Chapter 8: Boundaries

Description: Capture library behavior in focused learning tests.

TypeScript:

```ts
expect(logger.levelFor('billing')).toBe('info');
```

Python:

```python
assert logger.level_for('billing') == 'info'
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-123 Learning Tests Are Better Than Free

Topic: Chapter 8: Boundaries

Description: Keep learning tests as upgrade alarms for third-party behavior.

TypeScript:

```ts
it('parses provider timeout errors', () => expect(parseError(timeout)).toEqual(retryable));
```

Python:

```python
def test_parses_provider_timeout_errors():
    assert parse_error(timeout) == retryable
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-124 Using Code That Does Not Yet Exist

Topic: Chapter 8: Boundaries

Description: Define the interface you wish you had, then adapt the eventual dependency to it.

TypeScript:

```ts
interface MarketData { latestPrice(pair: Pair): Promise<Money>; }
```

Python:

```python
class MarketData(Protocol):
    def latest_price(self, pair: Pair) -> Money: ...
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-125 Clean Boundaries

Topic: Chapter 8: Boundaries

Description: Keep boundary translation in one place.

TypeScript:

```ts
return toDomainOrder(providerOrder);
```

Python:

```python
return to_domain_order(provider_order)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-126 Three Laws Of TDD

Topic: Chapter 9: Unit Tests

Description: Write a failing test before production behavior, then make it pass simply.

TypeScript:

```ts
expect(totalFor(emptyCart)).toEqual(money('0.00'));
```

Python:

```python
assert total_for(empty_cart) == Money('0.00')
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-127 Keeping Tests Clean

Topic: Chapter 9: Unit Tests

Description: Refactor tests so they remain readable and useful.

TypeScript:

```ts
expect(orderTotal(cartWith('book'))).toEqual(money('12.00'));
```

Python:

```python
assert order_total(cart_with('book')) == Money('12.00')
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-128 Tests Enable The Ilities

Topic: Chapter 9: Unit Tests

Description: Clean tests make refactoring, portability, and maintainability safer.

TypeScript:

```ts
await expectCheckoutToPublishReceipt(cart);
```

Python:

```python
expect_checkout_to_publish_receipt(cart)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-129 Clean Tests

Topic: Chapter 9: Unit Tests

Description: Make test setup, action, and assertion obvious.

TypeScript:

```ts
const receipt = await checkout(cart);
expect(receipt.total).toEqual(cart.total);
```

Python:

```python
receipt = checkout(cart)
assert receipt.total == cart.total
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-130 Domain Specific Testing Language

Topic: Chapter 9: Unit Tests

Description: Build test helpers that speak the domain.

TypeScript:

```ts
const cart = cartWithItems(item('book', '12.00'));
```

Python:

```python
cart = cart_with_items(item('book', '12.00'))
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-131 Dual Standard

Topic: Chapter 9: Unit Tests

Description: Tests may use concise helpers while production code stays explicit and robust.

TypeScript:

```ts
expect(renderedInvoice(invoice)).toContainTotal('12.00');
```

Python:

```python
assert rendered_invoice(invoice).contains_total('12.00')
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-132 One Assert Per Test

Topic: Chapter 9: Unit Tests

Description: Prefer tests that fail for one clear behavioral reason.

TypeScript:

```ts
expect(validatePassword('short')).toThrow(WeakPasswordError);
```

Python:

```python
with pytest.raises(WeakPasswordError):
    validate_password('short')
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-133 Single Concept Per Test

Topic: Chapter 9: Unit Tests

Description: Split unrelated examples into separate tests.

TypeScript:

```ts
it('rejects blank email', () => expectSignup({ email: '' }).toFail());
```

Python:

```python
def test_rejects_blank_email():
    assert_signup({'email': ''}).fails()
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-134 FIRST Tests

Topic: Chapter 9: Unit Tests

Description: Keep tests fast, independent, repeatable, self-validating, and timely.

TypeScript:

```ts
expect(calculateTax(order)).toEqual(money('0.83'));
```

Python:

```python
assert calculate_tax(order) == Money('0.83')
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-135 Class Organization

Topic: Chapter 10: Classes

Description: Order class members so readers see constants, state, public API, then private details.

TypeScript:

```ts
class Invoice {
  total(): Money { return this.subtotal.plus(this.tax); }
}
```

Python:

```python
class Invoice:
    def total(self) -> Money:
        return self.subtotal + self.tax
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-136 Encapsulation

Topic: Chapter 10: Classes

Description: Keep state private unless exposing it improves the design.

TypeScript:

```ts
class Counter {
  private value = 0;
  increment(): number { return ++this.value; }
}
```

Python:

```python
class Counter:
    def __init__(self) -> None:
        self._value = 0
    def increment(self) -> int:
        self._value += 1
        return self._value
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-137 Classes Should Be Small

Topic: Chapter 10: Classes

Description: A class should represent one narrow concept.

TypeScript:

```ts
class PasswordPolicy { accepts(password: string): boolean { return password.length >= 12; } }
```

Python:

```python
class PasswordPolicy:
    def accepts(self, password: str) -> bool:
        return len(password) >= 12
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-138 Single Responsibility Principle

Topic: Chapter 10: Classes

Description: Give a class one reason to change.

TypeScript:

```ts
class InvoicePrinter { print(invoice: Invoice): Pdf { return renderInvoice(invoice); } }
```

Python:

```python
class InvoicePrinter:
    def print(self, invoice: Invoice) -> Pdf:
        return render_invoice(invoice)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-139 Cohesion

Topic: Chapter 10: Classes

Description: Methods should share the same core state and purpose.

TypeScript:

```ts
class RetryPolicy { constructor(private max: number) {} shouldRetry(n: number) { return n < this.max; } }
```

Python:

```python
@dataclass
class RetryPolicy:
    max_attempts: int
    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-140 Many Small Classes

Topic: Chapter 10: Classes

Description: Split responsibilities when cohesion drops.

TypeScript:

```ts
const tax = taxCalculator.calculate(order);
```

Python:

```python
tax = tax_calculator.calculate(order)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-141 Organizing For Change

Topic: Chapter 10: Classes

Description: Place volatile policy behind interfaces or small modules.

TypeScript:

```ts
pricingPolicy.price(order);
```

Python:

```python
pricing_policy.price(order)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-142 Isolating From Change

Topic: Chapter 10: Classes

Description: Depend on stable abstractions at change-prone boundaries.

TypeScript:

```ts
constructor(private readonly rates: ExchangeRateProvider) {}
```

Python:

```python
def __init__(self, rates: ExchangeRateProvider) -> None:
    self._rates = rates
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-143 Build A City

Topic: Chapter 11: Systems

Description: Separate high-level system assembly from local component behavior.

TypeScript:

```ts
const app = createApp(container.resolve(OrderService));
```

Python:

```python
app = create_app(container.resolve(OrderService))
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-144 Separate Construction From Use

Topic: Chapter 11: Systems

Description: Construct dependencies at composition roots, not inside business logic.

TypeScript:

```ts
const service = new OrderService(repository, gateway);
```

Python:

```python
service = OrderService(repository, gateway)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-145 Separation Of Main

Topic: Chapter 11: Systems

Description: Keep main responsible for wiring, leaving behavior to application services.

TypeScript:

```ts
main().catch(reportStartupError);
```

Python:

```python
if __name__ == '__main__':
    main()
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-146 Factories

Topic: Chapter 11: Systems

Description: Use factories when creation is complex or policy-driven.

TypeScript:

```ts
const gateway = paymentGatewayFactory.forRegion(region);
```

Python:

```python
gateway = payment_gateway_factory.for_region(region)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-147 Dependency Injection

Topic: Chapter 11: Systems

Description: Pass dependencies in so modules are testable and replaceable.

TypeScript:

```ts
new CheckoutService(paymentGateway, orderRepository);
```

Python:

```python
CheckoutService(payment_gateway, order_repository)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-148 Scaling Up

Topic: Chapter 11: Systems

Description: Keep architecture evolvable by separating concerns before size demands it.

TypeScript:

```ts
orderModule.register(container);
```

Python:

```python
order_module.register(container)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-149 Cross-Cutting Concerns

Topic: Chapter 11: Systems

Description: Apply logging, metrics, and transactions outside core domain logic.

TypeScript:

```ts
withMetrics('checkout', () => checkout(order));
```

Python:

```python
with_metrics('checkout', lambda: checkout(order))
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-150 Java Proxies

Topic: Chapter 11: Systems

Description: Use proxy-like wrappers for narrow infrastructure concerns.

TypeScript:

```ts
const repository = withTracing(new SqlOrderRepository(db));
```

Python:

```python
repository = with_tracing(SqlOrderRepository(db))
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-151 Pure Java AOP Frameworks

Topic: Chapter 11: Systems

Description: Keep domain objects independent from framework aspect plumbing.

TypeScript:

```ts
bankAccount.withdraw(amount);
```

Python:

```python
bank_account.withdraw(amount)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-152 AspectJ Aspects

Topic: Chapter 11: Systems

Description: Modularize cross-cutting concerns without leaking them into domain code.

TypeScript:

```ts
@Transactional()
async function transfer(request: TransferRequest) { return transferFunds(request); }
```

Python:

```python
@transactional
def transfer(request: TransferRequest) -> Receipt:
    return transfer_funds(request)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-153 Test Drive System Architecture

Topic: Chapter 11: Systems

Description: Let tests pressure architecture through executable use cases.

TypeScript:

```ts
await expectCheckoutFlow().toPublishReceipt();
```

Python:

```python
expect_checkout_flow().to_publish_receipt()
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-154 Optimize Decision Making

Topic: Chapter 11: Systems

Description: Delay decisions until the code has enough information, while keeping options isolated.

TypeScript:

```ts
const store = featureFlags.useRedis ? redisStore : memoryStore;
```

Python:

```python
store = redis_store if feature_flags.use_redis else memory_store
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-155 Use Standards Wisely

Topic: Chapter 11: Systems

Description: Adopt standards when they add real integration value, not ceremony.

TypeScript:

```ts
const event = CloudEvent.fromDomain(orderSubmitted(order));
```

Python:

```python
event = CloudEvent.from_domain(order_submitted(order))
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-156 Systems Need DSLs

Topic: Chapter 11: Systems

Description: Use small domain-specific APIs to express configuration and rules clearly.

TypeScript:

```ts
route.post('/orders').requiresAuth().handle(postOrder);
```

Python:

```python
route.post('/orders').requires_auth().handle(post_order)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-157 Getting Clean Via Emergent Design

Topic: Chapter 12: Emergence

Description: Let simple design emerge from tests and refactoring.

TypeScript:

```ts
const total = priceCart(cart);
```

Python:

```python
total = price_cart(cart)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-158 Runs All The Tests

Topic: Chapter 12: Emergence

Description: A design is not safe to improve unless tests protect behavior.

TypeScript:

```ts
expect(calculateFee(amount)).toEqual(expectedFee);
```

Python:

```python
assert calculate_fee(amount) == expected_fee
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-159 Refactoring Rules

Topic: Chapter 12: Emergence

Description: After tests pass, remove duplication and clarify intent.

TypeScript:

```ts
const fee = feePolicy.calculate(amount);
```

Python:

```python
fee = fee_policy.calculate(amount)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-160 No Duplication

Topic: Chapter 12: Emergence

Description: Eliminate duplicated knowledge, not just duplicated text.

TypeScript:

```ts
const canRetry = retryPolicy.shouldRetry(error, attempt);
```

Python:

```python
can_retry = retry_policy.should_retry(error, attempt)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-161 Expressive Design

Topic: Chapter 12: Emergence

Description: Make code reveal business intent directly.

TypeScript:

```ts
if (subscription.isRenewable(now)) renew(subscription);
```

Python:

```python
if subscription.is_renewable(now):
    renew(subscription)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-162 Minimal Classes And Methods

Topic: Chapter 12: Emergence

Description: Do not add abstractions until they earn their cost.

TypeScript:

```ts
function formatSku(sku: string): string { return sku.trim().toUpperCase(); }
```

Python:

```python
def format_sku(sku: str) -> str:
    return sku.strip().upper()
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-163 Why Concurrency

Topic: Chapter 13: Concurrency

Description: Use concurrency to improve responsiveness or throughput, not as decoration.

TypeScript:

```ts
await Promise.all([loadProfile(id), loadPermissions(id)]);
```

Python:

```python
await asyncio.gather(load_profile(user_id), load_permissions(user_id))
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-164 Myths And Misconceptions

Topic: Chapter 13: Concurrency

Description: Do not assume concurrent code is automatically faster or simpler.

TypeScript:

```ts
const result = await runBoundedConcurrency(tasks, 4);
```

Python:

```python
result = await run_bounded_concurrency(tasks, limit=4)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-165 Concurrency Challenges

Topic: Chapter 13: Concurrency

Description: Make shared state and ordering assumptions explicit.

TypeScript:

```ts
await accountLock.runExclusive(accountId, () => debit(accountId, amount));
```

Python:

```python
async with account_lock.for_key(account_id):
    await debit(account_id, amount)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-166 Concurrency Defense Principles

Topic: Chapter 13: Concurrency

Description: Keep concurrent responsibilities separate from business logic.

TypeScript:

```ts
workerPool.enqueue(() => sendReceipt(receipt));
```

Python:

```python
worker_pool.enqueue(lambda: send_receipt(receipt))
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-167 Concurrency SRP

Topic: Chapter 13: Concurrency

Description: Keep thread orchestration separate from domain behavior.

TypeScript:

```ts
await orderWorker.process(orderJob);
```

Python:

```python
await order_worker.process(order_job)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-168 Limit Scope Of Data

Topic: Chapter 13: Concurrency

Description: Restrict shared mutable data to the smallest possible scope.

TypeScript:

```ts
await lock.runExclusive(() => cache.set(key, value));
```

Python:

```python
async with lock:
    cache[key] = value
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-169 Use Copies Of Data

Topic: Chapter 13: Concurrency

Description: Pass immutable snapshots into concurrent work.

TypeScript:

```ts
const snapshot = structuredClone(order);
await processOrderSnapshot(snapshot);
```

Python:

```python
snapshot = copy.deepcopy(order)
await process_order_snapshot(snapshot)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-170 Threads Independent

Topic: Chapter 13: Concurrency

Description: Design concurrent workers to share little or nothing.

TypeScript:

```ts
await Promise.all(jobs.map((job) => processJob(job)));
```

Python:

```python
await asyncio.gather(*(process_job(job) for job in jobs))
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-171 Know Your Library

Topic: Chapter 13: Concurrency

Description: Use well-tested concurrency primitives instead of hand-rolled coordination.

TypeScript:

```ts
const queue = new PQueue({ concurrency: 4 });
```

Python:

```python
queue = asyncio.Queue(maxsize=100)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-172 Thread-Safe Collections

Topic: Chapter 13: Concurrency

Description: Use safe collections or queues for shared work.

TypeScript:

```ts
await workQueue.add(job);
```

Python:

```python
await work_queue.put(job)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-173 Know Execution Models

Topic: Chapter 13: Concurrency

Description: Name the concurrency model so code matches the expected flow.

TypeScript:

```ts
producer.publish(job);
consumer.start(processJob);
```

Python:

```python
producer.publish(job)
consumer.start(process_job)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-174 Producer Consumer

Topic: Chapter 13: Concurrency

Description: Separate producers of work from consumers that process work.

TypeScript:

```ts
await queue.enqueue(orderJob);
```

Python:

```python
await queue.put(order_job)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-175 Readers Writers

Topic: Chapter 13: Concurrency

Description: Use read/write locks when many readers and few writers share state.

TypeScript:

```ts
await readWriteLock.read(() => cache.get(key));
```

Python:

```python
async with read_write_lock.read():
    value = cache[key]
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-176 Dining Philosophers

Topic: Chapter 13: Concurrency

Description: Acquire multiple resources in a stable order to avoid deadlocks.

TypeScript:

```ts
const [first, second] = orderedLocks(accountA, accountB);
```

Python:

```python
first, second = ordered_locks(account_a, account_b)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-177 Dependencies Between Synchronized Methods

Topic: Chapter 13: Concurrency

Description: Avoid requiring callers to coordinate multiple locked methods correctly.

TypeScript:

```ts
await accountStore.transfer(fromId, toId, amount);
```

Python:

```python
await account_store.transfer(from_id, to_id, amount)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-178 Small Synchronized Sections

Topic: Chapter 13: Concurrency

Description: Keep locked sections minimal and side-effect focused.

TypeScript:

```ts
await lock.runExclusive(() => updateBalance(accountId, amount));
```

Python:

```python
async with lock:
    update_balance(account_id, amount)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-179 Correct Shutdown Is Hard

Topic: Chapter 13: Concurrency

Description: Make shutdown explicit and testable.

TypeScript:

```ts
await worker.stop({ drain: true, timeoutMs: 5000 });
```

Python:

```python
await worker.stop(drain=True, timeout=5)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-180 Testing Threaded Code

Topic: Chapter 13: Concurrency

Description: Stress concurrency with repeatable tests and controlled scheduling.

TypeScript:

```ts
await runRaceTest(() => transferBothWays(accounts));
```

Python:

```python
await run_race_test(lambda: transfer_both_ways(accounts))
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-181 Spurious Failures Are Threading Issues

Topic: Chapter 13: Concurrency

Description: Treat flaky concurrent failures as real signals.

TypeScript:

```ts
await repeat(100, () => transferScenario());
```

Python:

```python
await repeat(100, transfer_scenario)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-182 Get Nonthreaded Code Working First

Topic: Chapter 13: Concurrency

Description: Verify domain behavior before adding concurrent execution.

TypeScript:

```ts
expect(applyPayment(order, payment)).toEqual(paidOrder);
```

Python:

```python
assert apply_payment(order, payment) == paid_order
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-183 Threaded Code Pluggable

Topic: Chapter 13: Concurrency

Description: Make concurrency strategy replaceable in tests.

TypeScript:

```ts
const executor = new InlineExecutor();
await service.run(executor);
```

Python:

```python
executor = InlineExecutor()
await service.run(executor)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-184 Threaded Code Tunable

Topic: Chapter 13: Concurrency

Description: Expose safe tuning parameters at configuration boundaries.

TypeScript:

```ts
const pool = new WorkerPool({ concurrency: settings.workerCount });
```

Python:

```python
pool = WorkerPool(concurrency=settings.worker_count)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-185 Run More Threads Than Processors

Topic: Chapter 13: Concurrency

Description: Stress tests should oversubscribe work to expose scheduling defects.

TypeScript:

```ts
await runWithConcurrency(tasks, cpuCount() * 4);
```

Python:

```python
await run_with_concurrency(tasks, os.cpu_count() * 4)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-186 Run On Different Platforms

Topic: Chapter 13: Concurrency

Description: Avoid platform-specific concurrency assumptions.

TypeScript:

```ts
await portableScheduler.run(job);
```

Python:

```python
await portable_scheduler.run(job)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-187 Instrument To Force Failures

Topic: Chapter 13: Concurrency

Description: Add test-only hooks to widen race windows intentionally.

TypeScript:

```ts
await scheduler.yieldAt('after-read');
```

Python:

```python
await scheduler.yield_at('after_read')
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-188 Hand Coded Instrumentation

Topic: Chapter 13: Concurrency

Description: Use explicit test probes when diagnosing races.

TypeScript:

```ts
testProbe.pause('before-write');
```

Python:

```python
test_probe.pause('before_write')
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-189 Automated Instrumentation

Topic: Chapter 13: Concurrency

Description: Use tools that vary scheduling automatically when possible.

TypeScript:

```ts
await concurrencyFuzzer.run(transferScenario);
```

Python:

```python
await concurrency_fuzzer.run(transfer_scenario)
```

Lint candidates: Flag shared mutable state in async/concurrent code and require named locks, queues, or immutable snapshots.

## CC-190 Args Implementation

Topic: Chapter 14: Successive Refinement

Description: Let a working parser evolve through tests and small refactors.

TypeScript:

```ts
const args = parseArgs(schema, argv);
```

Python:

```python
args = parse_args(schema, argv)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-191 How Did I Do This

Topic: Chapter 14: Successive Refinement

Description: Make refactoring steps understandable by keeping behavior protected.

TypeScript:

```ts
expect(parseArgs(schema, ['--port', '8080']).port).toBe(8080);
```

Python:

```python
assert parse_args(schema, ['--port', '8080']).port == 8080
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-192 Args Rough Draft

Topic: Chapter 14: Successive Refinement

Description: Accept that first drafts are rough, then refine with tests.

TypeScript:

```ts
const parsed = roughParseArgs(argv);
```

Python:

```python
parsed = rough_parse_args(argv)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-193 So I Stopped

Topic: Chapter 14: Successive Refinement

Description: Pause when code resists change and improve structure before adding more behavior.

TypeScript:

```ts
const parser = new ArgsParser(schema);
```

Python:

```python
parser = ArgsParser(schema)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-194 On Incrementalism

Topic: Chapter 14: Successive Refinement

Description: Move in small verified steps rather than one large rewrite.

TypeScript:

```ts
const option = parseBooleanOption(token);
```

Python:

```python
option = parse_boolean_option(token)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-195 String Arguments

Topic: Chapter 14: Successive Refinement

Description: Add new argument types by extending a clear parser structure.

TypeScript:

```ts
schema.addString('output');
```

Python:

```python
schema.add_string('output')
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-196 JUnit Framework

Topic: Chapter 15: JUnit Internals

Description: Study framework internals by identifying small roles and collaborations.

TypeScript:

```ts
const result = testRunner.run(testCase);
```

Python:

```python
result = test_runner.run(test_case)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-197 First Make It Work

Topic: Chapter 16: Refactoring SerialDate

Description: Before refactoring, pin current behavior with tests.

TypeScript:

```ts
expect(addDays(date, 1)).toEqual(nextDate);
```

Python:

```python
assert add_days(date, 1) == next_date
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-198 Then Make It Right

Topic: Chapter 16: Refactoring SerialDate

Description: After behavior is safe, improve names, structure, and boundaries.

TypeScript:

```ts
const nextBusinessDay = calendar.nextBusinessDay(date);
```

Python:

```python
next_business_day = calendar.next_business_day(date)
```

Lint candidates: Use semantic search metadata first; automate only when the pattern has a low false-positive rate.

## CC-199 C1 Inappropriate Information

Topic: Chapter 17: Smells and Heuristics - Comments

Description: Keep comments focused on local code, not unrelated project history.

TypeScript:

```ts
const timeoutMs = settings.gatewayTimeoutMs;
```

Python:

```python
timeout_ms = settings.gateway_timeout_ms
```

Lint candidates: Candidate lint/search rule: Keep comments focused on local code, not unrelated project history.

## CC-200 C2 Obsolete Comment

Topic: Chapter 17: Smells and Heuristics - Comments

Description: Delete comments that no longer match behavior.

TypeScript:

```ts
const retryDelay = retryPolicy.delayFor(attempt);
```

Python:

```python
retry_delay = retry_policy.delay_for(attempt)
```

Lint candidates: Candidate lint/search rule: Delete comments that no longer match behavior.

## CC-201 C3 Redundant Comment

Topic: Chapter 17: Smells and Heuristics - Comments

Description: Remove comments that repeat the code.

TypeScript:

```ts
return customer.isActive;
```

Python:

```python
return customer.is_active
```

Lint candidates: Candidate lint/search rule: Remove comments that repeat the code.

## CC-202 C4 Poorly Written Comment

Topic: Chapter 17: Smells and Heuristics - Comments

Description: Rewrite or remove vague comments that do not explain a clear constraint.

TypeScript:

```ts
const normalizedSku = normalizeSku(sku);
```

Python:

```python
normalized_sku = normalize_sku(sku)
```

Lint candidates: Candidate lint/search rule: Rewrite or remove vague comments that do not explain a clear constraint.

## CC-203 C5 Commented Out Code

Topic: Chapter 17: Smells and Heuristics - Comments

Description: Delete commented code and rely on version history.

TypeScript:

```ts
await publishReceipt(receipt);
```

Python:

```python
publish_receipt(receipt)
```

Lint candidates: Candidate lint/search rule: Delete commented code and rely on version history.

## CC-204 E1 Build Requires More Than One Step

Topic: Chapter 17: Smells and Heuristics - Environment

Description: Provide one command that builds the project reproducibly.

TypeScript:

```ts
await runCommand('npm run build');
```

Python:

```python
run_command('python -m build')
```

Lint candidates: Candidate lint/search rule: Provide one command that builds the project reproducibly.

## CC-205 E2 Tests Require More Than One Step

Topic: Chapter 17: Smells and Heuristics - Environment

Description: Provide one command that runs the test suite reproducibly.

TypeScript:

```ts
await runCommand('npm test');
```

Python:

```python
run_command('pytest')
```

Lint candidates: Candidate lint/search rule: Provide one command that runs the test suite reproducibly.

## CC-206 F1 Too Many Arguments

Topic: Chapter 17: Smells and Heuristics - Functions

Description: Group cohesive parameters or introduce a value object.

TypeScript:

```ts
createDelivery(orderId, deliveryWindow);
```

Python:

```python
create_delivery(order_id, delivery_window)
```

Lint candidates: Candidate lint/search rule: Group cohesive parameters or introduce a value object.

## CC-207 F2 Output Arguments

Topic: Chapter 17: Smells and Heuristics - Functions

Description: Return values instead of mutating output parameters.

TypeScript:

```ts
const enriched = enrichOrder(order);
```

Python:

```python
enriched = enrich_order(order)
```

Lint candidates: Candidate lint/search rule: Return values instead of mutating output parameters.

## CC-208 F3 Flag Arguments

Topic: Chapter 17: Smells and Heuristics - Functions

Description: Replace boolean modes with named functions.

TypeScript:

```ts
renderCompactInvoice(invoice);
```

Python:

```python
render_compact_invoice(invoice)
```

Lint candidates: Candidate lint/search rule: Replace boolean modes with named functions.

## CC-209 F4 Dead Function

Topic: Chapter 17: Smells and Heuristics - Functions

Description: Remove unused functions instead of preserving them just in case.

TypeScript:

```ts
export function activeFormatter(value: Money): string { return value.format(); }
```

Python:

```python
def active_formatter(value: Money) -> str:
    return value.format()
```

Lint candidates: Candidate lint/search rule: Remove unused functions instead of preserving them just in case.

## CC-210 G1 Multiple Languages In One Source File

Topic: Chapter 17: Smells and Heuristics - General

Description: Do not mix templates, SQL, and application code without boundaries.

TypeScript:

```ts
const query = ordersQuery.byCustomer(customerId);
```

Python:

```python
query = orders_query.by_customer(customer_id)
```

Lint candidates: Candidate lint/search rule: Do not mix templates, SQL, and application code without boundaries.

## CC-211 G2 Obvious Behavior Unimplemented

Topic: Chapter 17: Smells and Heuristics - General

Description: Implement behavior implied by names and tests.

TypeScript:

```ts
if (cart.isEmpty()) return EmptyCartTotal;
```

Python:

```python
if cart.is_empty():
    return EMPTY_CART_TOTAL
```

Lint candidates: Candidate lint/search rule: Implement behavior implied by names and tests.

## CC-212 G3 Incorrect Boundary Behavior

Topic: Chapter 17: Smells and Heuristics - General

Description: Test and handle edges explicitly.

TypeScript:

```ts
return clamp(discount, MIN_DISCOUNT, MAX_DISCOUNT);
```

Python:

```python
return clamp(discount, MIN_DISCOUNT, MAX_DISCOUNT)
```

Lint candidates: Candidate lint/search rule: Test and handle edges explicitly.

## CC-213 G4 Overridden Safeties

Topic: Chapter 17: Smells and Heuristics - General

Description: Do not suppress type, lint, or runtime safety without a local reason.

TypeScript:

```ts
const amount = Money.parse(input.amount);
```

Python:

```python
amount = Money.parse(payload['amount'])
```

Lint candidates: Candidate lint/search rule: Do not suppress type, lint, or runtime safety without a local reason.

## CC-214 G5 Duplication

Topic: Chapter 17: Smells and Heuristics - General

Description: Remove repeated knowledge behind one named abstraction.

TypeScript:

```ts
return feePolicy.calculate(amount);
```

Python:

```python
return fee_policy.calculate(amount)
```

Lint candidates: Candidate lint/search rule: Remove repeated knowledge behind one named abstraction.

## CC-215 G6 Wrong Abstraction Level

Topic: Chapter 17: Smells and Heuristics - General

Description: Do not mix policy with low-level mechanics.

TypeScript:

```ts
return renewalPolicy.canRenew(subscription, now);
```

Python:

```python
return renewal_policy.can_renew(subscription, now)
```

Lint candidates: Candidate lint/search rule: Do not mix policy with low-level mechanics.

## CC-216 G7 Base Depends On Derivative

Topic: Chapter 17: Smells and Heuristics - General

Description: Keep base abstractions independent from specific implementations.

TypeScript:

```ts
interface Storage { save(record: Record): Promise<void>; }
```

Python:

```python
class Storage(Protocol):
    def save(self, record: Record) -> None: ...
```

Lint candidates: Candidate lint/search rule: Keep base abstractions independent from specific implementations.

## CC-217 G8 Too Much Information

Topic: Chapter 17: Smells and Heuristics - General

Description: Expose the smallest useful public API.

TypeScript:

```ts
order.cancel(reason);
```

Python:

```python
order.cancel(reason)
```

Lint candidates: Candidate lint/search rule: Expose the smallest useful public API.

## CC-218 G9 Dead Code

Topic: Chapter 17: Smells and Heuristics - General

Description: Remove unreachable or unused code.

TypeScript:

```ts
return activeRules.filter(rule => rule.applies(order));
```

Python:

```python
return [rule for rule in active_rules if rule.applies(order)]
```

Lint candidates: Candidate lint/search rule: Remove unreachable or unused code.

## CC-219 G10 Vertical Separation

Topic: Chapter 17: Smells and Heuristics - General

Description: Keep related concepts near each other.

TypeScript:

```ts
const tax = calculateTax(order);
const total = order.subtotal.plus(tax);
```

Python:

```python
tax = calculate_tax(order)
total = order.subtotal + tax
```

Lint candidates: Candidate lint/search rule: Keep related concepts near each other.

## CC-220 G11 Inconsistency

Topic: Chapter 17: Smells and Heuristics - General

Description: Use the same style for the same idea.

TypeScript:

```ts
fetchCustomer(customerId);
```

Python:

```python
fetch_customer(customer_id)
```

Lint candidates: Candidate lint/search rule: Use the same style for the same idea.

## CC-221 G12 Clutter

Topic: Chapter 17: Smells and Heuristics - General

Description: Remove unused variables, empty constructors, and redundant wrappers.

TypeScript:

```ts
return normalizeEmail(email);
```

Python:

```python
return normalize_email(email)
```

Lint candidates: Candidate lint/search rule: Remove unused variables, empty constructors, and redundant wrappers.

## CC-222 G13 Artificial Coupling

Topic: Chapter 17: Smells and Heuristics - General

Description: Do not make unrelated modules depend on each other for convenience.

TypeScript:

```ts
taxCalculator.calculate(order);
```

Python:

```python
tax_calculator.calculate(order)
```

Lint candidates: Candidate lint/search rule: Do not make unrelated modules depend on each other for convenience.

## CC-223 G14 Feature Envy

Topic: Chapter 17: Smells and Heuristics - General

Description: Move behavior close to the data it uses most.

TypeScript:

```ts
order.total();
```

Python:

```python
order.total()
```

Lint candidates: Candidate lint/search rule: Move behavior close to the data it uses most.

## CC-224 G15 Selector Arguments

Topic: Chapter 17: Smells and Heuristics - General

Description: Replace selector parameters with polymorphism or named operations.

TypeScript:

```ts
exportCsv(report);
```

Python:

```python
export_csv(report)
```

Lint candidates: Candidate lint/search rule: Replace selector parameters with polymorphism or named operations.

## CC-225 G16 Obscured Intent

Topic: Chapter 17: Smells and Heuristics - General

Description: Name intermediate concepts in dense logic.

TypeScript:

```ts
const canRefund = order.isPaid && withinRefundWindow(order, now);
```

Python:

```python
can_refund = order.is_paid and within_refund_window(order, now)
```

Lint candidates: Candidate lint/search rule: Name intermediate concepts in dense logic.

## CC-226 G17 Misplaced Responsibility

Topic: Chapter 17: Smells and Heuristics - General

Description: Put behavior in the module that owns the concept.

TypeScript:

```ts
invoice.markPaid(payment);
```

Python:

```python
invoice.mark_paid(payment)
```

Lint candidates: Candidate lint/search rule: Put behavior in the module that owns the concept.

## CC-227 G18 Inappropriate Static

Topic: Chapter 17: Smells and Heuristics - General

Description: Avoid static/global state for behavior that needs dependencies or tests.

TypeScript:

```ts
new ExchangeRateService(rateProvider).convert(amount, currency);
```

Python:

```python
ExchangeRateService(rate_provider).convert(amount, currency)
```

Lint candidates: Candidate lint/search rule: Avoid static/global state for behavior that needs dependencies or tests.

## CC-228 G19 Explanatory Variables

Topic: Chapter 17: Smells and Heuristics - General

Description: Use local names to explain subexpressions.

TypeScript:

```ts
const isRenewalDue = subscription.expiresAt <= now;
```

Python:

```python
is_renewal_due = subscription.expires_at <= now
```

Lint candidates: Candidate lint/search rule: Use local names to explain subexpressions.

## CC-229 G20 Function Names Say What They Do

Topic: Chapter 17: Smells and Heuristics - General

Description: Rename vague functions to describe their actual effect.

TypeScript:

```ts
archiveExpiredSessions();
```

Python:

```python
archive_expired_sessions()
```

Lint candidates: Candidate lint/search rule: Rename vague functions to describe their actual effect.

## CC-230 G21 Understand The Algorithm

Topic: Chapter 17: Smells and Heuristics - General

Description: Refactor only after you can explain the algorithm with tests.

TypeScript:

```ts
const allocation = allocatePaymentsOldestFirst(payments, invoices);
```

Python:

```python
allocation = allocate_payments_oldest_first(payments, invoices)
```

Lint candidates: Candidate lint/search rule: Refactor only after you can explain the algorithm with tests.

## CC-231 G22 Make Logical Dependencies Physical

Topic: Chapter 17: Smells and Heuristics - General

Description: Pass required dependencies explicitly.

TypeScript:

```ts
priceOrder(order, pricingRules);
```

Python:

```python
price_order(order, pricing_rules)
```

Lint candidates: Candidate lint/search rule: Pass required dependencies explicitly.

## CC-232 G23 Prefer Polymorphism

Topic: Chapter 17: Smells and Heuristics - General

Description: Use dispatch or polymorphism for repeated type branching.

TypeScript:

```ts
handlerFor(order.type).submit(order);
```

Python:

```python
handler_for(order.type).submit(order)
```

Lint candidates: Candidate lint/search rule: Use dispatch or polymorphism for repeated type branching.

## CC-233 G24 Follow Standard Conventions

Topic: Chapter 17: Smells and Heuristics - General

Description: Follow local and language conventions consistently.

TypeScript:

```ts
const createdAt = new Date();
```

Python:

```python
created_at = datetime.now(tz=UTC)
```

Lint candidates: Candidate lint/search rule: Follow local and language conventions consistently.

## CC-234 G25 Named Constants

Topic: Chapter 17: Smells and Heuristics - General

Description: Replace magic numbers with named constants.

TypeScript:

```ts
if (attempts >= MAX_RETRY_ATTEMPTS) stopRetrying();
```

Python:

```python
if attempts >= MAX_RETRY_ATTEMPTS:
    stop_retrying()
```

Lint candidates: Candidate lint/search rule: Replace magic numbers with named constants.

## CC-235 G26 Be Precise

Topic: Chapter 17: Smells and Heuristics - General

Description: Use exact types, units, and boundary rules.

TypeScript:

```ts
const timeoutMs: Milliseconds = 3000;
```

Python:

```python
timeout_seconds: float = 3.0
```

Lint candidates: Candidate lint/search rule: Use exact types, units, and boundary rules.

## CC-236 G27 Structure Over Convention

Topic: Chapter 17: Smells and Heuristics - General

Description: Represent rules in code structure rather than naming conventions alone.

TypeScript:

```ts
const command = new SubmitOrderCommand(orderId);
```

Python:

```python
command = SubmitOrderCommand(order_id)
```

Lint candidates: Candidate lint/search rule: Represent rules in code structure rather than naming conventions alone.

## CC-237 G28 Encapsulate Conditionals

Topic: Chapter 17: Smells and Heuristics - General

Description: Hide complex conditions behind named predicates.

TypeScript:

```ts
if (canRetryPayment(error, attempt)) retry();
```

Python:

```python
if can_retry_payment(error, attempt):
    retry()
```

Lint candidates: Candidate lint/search rule: Hide complex conditions behind named predicates.

## CC-238 G29 Avoid Negative Conditionals

Topic: Chapter 17: Smells and Heuristics - General

Description: Prefer positive predicates and branches.

TypeScript:

```ts
if (account.isActive) allowTransfer(account);
```

Python:

```python
if account.is_active:
    allow_transfer(account)
```

Lint candidates: Candidate lint/search rule: Prefer positive predicates and branches.

## CC-239 G30 Functions Do One Thing

Topic: Chapter 17: Smells and Heuristics - General

Description: Split functions that validate, transform, persist, and notify.

TypeScript:

```ts
const order = buildOrder(validatedInput);
```

Python:

```python
order = build_order(validated_input)
```

Lint candidates: Candidate lint/search rule: Split functions that validate, transform, persist, and notify.

## CC-240 G31 Hidden Temporal Couplings

Topic: Chapter 17: Smells and Heuristics - General

Description: Make ordering requirements explicit in names or types.

TypeScript:

```ts
const session = await authenticatedSession(credentials);
```

Python:

```python
session = authenticated_session(credentials)
```

Lint candidates: Candidate lint/search rule: Make ordering requirements explicit in names or types.

## CC-241 G32 Do Not Be Arbitrary

Topic: Chapter 17: Smells and Heuristics - General

Description: Keep structure tied to a real reason, not personal taste.

TypeScript:

```ts
const retryPolicy = RetryPolicy.standard();
```

Python:

```python
retry_policy = RetryPolicy.standard()
```

Lint candidates: Candidate lint/search rule: Keep structure tied to a real reason, not personal taste.

## CC-242 G33 Encapsulate Boundary Conditions

Topic: Chapter 17: Smells and Heuristics - General

Description: Name edge rules and keep them in one place.

TypeScript:

```ts
return isWithinRefundWindow(order, now);
```

Python:

```python
return is_within_refund_window(order, now)
```

Lint candidates: Candidate lint/search rule: Name edge rules and keep them in one place.

## CC-243 G34 One Abstraction Level

Topic: Chapter 17: Smells and Heuristics - General

Description: Keep each function at one abstraction level.

TypeScript:

```ts
return submitPricedOrder(priceOrder(order));
```

Python:

```python
return submit_priced_order(price_order(order))
```

Lint candidates: Candidate lint/search rule: Keep each function at one abstraction level.

## CC-244 G35 Configurable Data High

Topic: Chapter 17: Smells and Heuristics - General

Description: Keep configuration values near startup or module configuration.

TypeScript:

```ts
const settings = loadPaymentSettings(env);
```

Python:

```python
settings = load_payment_settings(env)
```

Lint candidates: Candidate lint/search rule: Keep configuration values near startup or module configuration.

## CC-245 G36 Avoid Transitive Navigation

Topic: Chapter 17: Smells and Heuristics - General

Description: Avoid chains that expose object internals.

TypeScript:

```ts
const region = customer.billingRegion();
```

Python:

```python
region = customer.billing_region()
```

Lint candidates: Candidate lint/search rule: Avoid chains that expose object internals.

## CC-246 J1 Avoid Long Import Lists

Topic: Chapter 17: Smells and Heuristics - Java

Description: Prefer module-level imports that keep dependency lists readable in languages that support them.

TypeScript:

```ts
import { OrderService } from './orders';
```

Python:

```python
from orders import OrderService
```

Lint candidates: Candidate lint/search rule: Prefer module-level imports that keep dependency lists readable in languages that support them.

## CC-247 J2 Do Not Inherit Constants

Topic: Chapter 17: Smells and Heuristics - Java

Description: Use explicit constants modules or enums instead of inherited constant bags.

TypeScript:

```ts
OrderStatus.Paid
```

Python:

```python
OrderStatus.PAID
```

Lint candidates: Candidate lint/search rule: Use explicit constants modules or enums instead of inherited constant bags.

## CC-248 J3 Constants Versus Enums

Topic: Chapter 17: Smells and Heuristics - Java

Description: Use enums for closed sets with meaning.

TypeScript:

```ts
enum OrderStatus { Draft, Paid, Cancelled }
```

Python:

```python
class OrderStatus(Enum):
    DRAFT = 'draft'
    PAID = 'paid'
```

Lint candidates: Candidate lint/search rule: Use enums for closed sets with meaning.

## CC-249 N1 Descriptive Names

Topic: Chapter 17: Smells and Heuristics - Names

Description: Choose names that reveal intent.

TypeScript:

```ts
const overdueInvoices = invoices.filter(isOverdue);
```

Python:

```python
overdue_invoices = [invoice for invoice in invoices if is_overdue(invoice)]
```

Lint candidates: Candidate lint/search rule: Choose names that reveal intent.

## CC-250 N2 Names At Appropriate Abstraction

Topic: Chapter 17: Smells and Heuristics - Names

Description: Name things at the level callers need.

TypeScript:

```ts
const settlement = settlementPolicy.settle(order);
```

Python:

```python
settlement = settlement_policy.settle(order)
```

Lint candidates: Candidate lint/search rule: Name things at the level callers need.

## CC-251 N3 Standard Nomenclature

Topic: Chapter 17: Smells and Heuristics - Names

Description: Use established names for known patterns and domain terms.

TypeScript:

```ts
class OrderRepository {}
```

Python:

```python
class OrderRepository: pass
```

Lint candidates: Candidate lint/search rule: Use established names for known patterns and domain terms.

## CC-252 N4 Unambiguous Names

Topic: Chapter 17: Smells and Heuristics - Names

Description: Avoid names that can mean multiple things.

TypeScript:

```ts
const billingAddress = customer.billingAddress;
```

Python:

```python
billing_address = customer.billing_address
```

Lint candidates: Candidate lint/search rule: Avoid names that can mean multiple things.

## CC-253 N5 Long Names Long Scopes

Topic: Chapter 17: Smells and Heuristics - Names

Description: Use longer names when a variable lives farther from its declaration.

TypeScript:

```ts
const pendingSettlementTransactions = loadPendingSettlementTransactions();
```

Python:

```python
pending_settlement_transactions = load_pending_settlement_transactions()
```

Lint candidates: Candidate lint/search rule: Use longer names when a variable lives farther from its declaration.

## CC-254 N6 Avoid Encodings

Topic: Chapter 17: Smells and Heuristics - Names

Description: Do not encode type or scope prefixes into names.

TypeScript:

```ts
const customerIds = customers.map(customer => customer.id);
```

Python:

```python
customer_ids = [customer.id for customer in customers]
```

Lint candidates: Candidate lint/search rule: Do not encode type or scope prefixes into names.

## CC-255 N7 Names Describe Side Effects

Topic: Chapter 17: Smells and Heuristics - Names

Description: Function names should reveal mutation or I/O.

TypeScript:

```ts
saveAndPublishOrder(order);
```

Python:

```python
save_and_publish_order(order)
```

Lint candidates: Candidate lint/search rule: Function names should reveal mutation or I/O.

## CC-256 T1 Insufficient Tests

Topic: Chapter 17: Smells and Heuristics - Tests

Description: Cover expected behavior, failure paths, and important edges.

TypeScript:

```ts
expect(calculateFee(zero)).toEqual(MINIMUM_FEE);
```

Python:

```python
assert calculate_fee(zero) == MINIMUM_FEE
```

Lint candidates: Candidate lint/search rule: Cover expected behavior, failure paths, and important edges.

## CC-257 T2 Use Coverage Tool

Topic: Chapter 17: Smells and Heuristics - Tests

Description: Use coverage to discover untested areas, then add meaningful tests.

TypeScript:

```ts
expect(coverage.forFile('pricing')).toBeGreaterThan(90);
```

Python:

```python
assert coverage.for_file('pricing') > 90
```

Lint candidates: Candidate lint/search rule: Use coverage to discover untested areas, then add meaningful tests.

## CC-258 T3 Do Not Skip Trivial Tests

Topic: Chapter 17: Smells and Heuristics - Tests

Description: Small obvious rules still deserve tests when they carry policy.

TypeScript:

```ts
expect(isBusinessDay(saturday)).toBe(false);
```

Python:

```python
assert not is_business_day(saturday)
```

Lint candidates: Candidate lint/search rule: Small obvious rules still deserve tests when they carry policy.

## CC-259 T4 Ignored Test Signals Ambiguity

Topic: Chapter 17: Smells and Heuristics - Tests

Description: Treat skipped tests as unresolved questions.

TypeScript:

```ts
it('documents the disputed rounding rule', () => expect(roundTax(value)).toEqual(expected));
```

Python:

```python
def test_documents_disputed_rounding_rule():
    assert round_tax(value) == expected
```

Lint candidates: Candidate lint/search rule: Treat skipped tests as unresolved questions.

## CC-260 T5 Test Boundary Conditions

Topic: Chapter 17: Smells and Heuristics - Tests

Description: Test just below, at, and just above important limits.

TypeScript:

```ts
expect(canWithdraw(MINIMUM_WITHDRAWAL)).toBe(true);
```

Python:

```python
assert can_withdraw(MINIMUM_WITHDRAWAL)
```

Lint candidates: Candidate lint/search rule: Test just below, at, and just above important limits.

## CC-261 T6 Exhaustively Test Near Bugs

Topic: Chapter 17: Smells and Heuristics - Tests

Description: When a bug appears, test nearby cases too.

TypeScript:

```ts
expect(parseDate('2026-02-29')).toThrow(InvalidDateError);
```

Python:

```python
with pytest.raises(InvalidDateError):
    parse_date('2026-02-29')
```

Lint candidates: Candidate lint/search rule: When a bug appears, test nearby cases too.

## CC-262 T7 Failure Patterns Revealing

Topic: Chapter 17: Smells and Heuristics - Tests

Description: Look for repeated failure shapes and add targeted tests.

TypeScript:

```ts
expect(() => parseAmount('1,00')).toThrow(InvalidAmountError);
```

Python:

```python
with pytest.raises(InvalidAmountError):
    parse_amount('1,00')
```

Lint candidates: Candidate lint/search rule: Look for repeated failure shapes and add targeted tests.

## CC-263 T8 Coverage Patterns Revealing

Topic: Chapter 17: Smells and Heuristics - Tests

Description: Use uncovered branches to find missing behavior examples.

TypeScript:

```ts
expect(discountFor(newCustomer)).toEqual(NO_DISCOUNT);
```

Python:

```python
assert discount_for(new_customer) == NO_DISCOUNT
```

Lint candidates: Candidate lint/search rule: Use uncovered branches to find missing behavior examples.

## CC-264 T9 Tests Should Be Fast

Topic: Chapter 17: Smells and Heuristics - Tests

Description: Keep unit tests quick enough to run continuously.

TypeScript:

```ts
expect(priceOrder(order)).toEqual(expectedTotal);
```

Python:

```python
assert price_order(order) == expected_total
```

Lint candidates: Candidate lint/search rule: Keep unit tests quick enough to run continuously.
