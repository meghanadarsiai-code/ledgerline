# PROMPTS.md - Development Log

1. **Database URL Connection Fix:** Resolved Neon Postgres SSL requirement by configuring connection settings properly in Django settings.
2. **Idempotency Fingerprint Validation:** Added request payload hashing to ensure that reusing an existing `Idempotency-Key` with a modified amount correctly triggers a `422 Unprocessable Entity` response rather than returning stale cached data.
3. **Deadlock Prevention in Transfers:** Implemented sorted account ID locking (`_lock_accounts`) so that simultaneous cross-transfers between two accounts never deadlock.
4. **Append-Only Enforcement:** Created a custom PostgreSQL trigger (`ledger_entries_are_append_only`) to ensure database-level rejection of any UPDATE or DELETE statements on ledger records.
5. **Concurrency Test Verification:** Tested simultaneous multi-thread requests against account balances to verify that `select_for_update` correctly blocks race conditions and prevents negative balances.