# LedgerLine

A secure, append-only financial ledger system built with Django and PostgreSQL, guaranteeing that books always balance, duplicate requests never pay twice, and every transaction is strictly audited.

## Core Architecture
- **Atomicity:** All money movements (`deposit`, `withdraw`, `transfer`) occur inside strict database transactions (`transaction.atomic()`).
- **Concurrency Control:** Uses PostgreSQL row-level locks (`select_for_update`) ordered by account ID to prevent deadlocks and race conditions.
- **Idempotency:** Unique composite constraints (`user`, `key`) via `IdempotencyRecord` catch replayed HTTP requests and return the original response without moving money twice.
- **Tamper-Proof Ledger:** Enforced via a PostgreSQL trigger (`BEFORE UPDATE OR DELETE`) ensuring ledger entries are permanently append-only.

## Seed Logins (For Testing)
| Role | Username | Password |
|---|---|---|
| **Admin** | `admin` | `Password123!` |
| **Account Holder** | `holder1` | `Password123!` |
| **Auditor** | `auditor1` | `Password123!` |

## API Endpoints
- `POST /api/login/` - Authenticate session
- `POST /api/logout/` - End session
- `GET /api/accounts/` - List accessible accounts
- `GET /api/accounts/<id>/statement/` - Full ledger statement (debits, credits, refusals)
- `POST /api/deposit/` - Deposit funds (Requires `Idempotency-Key` header)
- `POST /api/withdraw/` - Withdraw funds (Requires `Idempotency-Key` header)
- `POST /api/transfer/` - Transfer funds between accounts (Requires `Idempotency-Key` header)