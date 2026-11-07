import hashlib
import json
import uuid
from dataclasses import dataclass

from django.db import transaction

from .models import Account, IdempotencyRecord, LedgerEntry, User

MAX_AMOUNT = 10**12  # paise


class BadRequest(Exception):
    """Malformed input or unknown account. Nothing is recorded."""

    def __init__(self, message, http_status=400):
        super().__init__(message)
        self.message = message
        self.http_status = http_status


@dataclass
class Result:
    http_status: int
    body: dict
    replayed: bool = False


def _check_amount(amount):
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise BadRequest("amount must be a whole number of paise")
    if not 1 <= amount <= MAX_AMOUNT:
        raise BadRequest("amount is out of range")
    return amount


def _check_id(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise BadRequest("account id must be a whole number")
    return value


def _check_key(key):
    if not isinstance(key, str) or not 1 <= len(key) <= 100:
        raise BadRequest("Idempotency-Key is required (1 to 100 characters)")
    return key


def _fingerprint(operation, **fields):
    raw = json.dumps({"op": operation, **fields}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _may_debit(user, account):
    """Only the owning account holder can take money out of an account."""
    return user.role == User.Role.HOLDER and account.owner_id == user.id


def _may_deposit(user, account):
    if user.role == User.Role.ADMIN:
        return True
    return user.role == User.Role.HOLDER and account.owner_id == user.id


def _lock_accounts(*ids):
    """Lock rows in id order, so two transfers can never wait on each other."""
    ordered = sorted(set(ids))
    rows = Account.objects.select_for_update().filter(id__in=ordered).order_by("id")
    found = {a.id: a for a in rows}
    if len(found) != len(ordered):
        raise BadRequest("account not found", 404)
    return found


def _refuse(user, account, kind, amount, reason, key, http_status, transfer_id=None):
    LedgerEntry.objects.create(
        account=account, kind=kind, status=LedgerEntry.Status.REFUSED,
        amount=amount, balance_after=None, transfer_id=transfer_id,
        initiated_by=user, idempotency_key=key, reason=reason,
    )
    return Result(http_status, {"status": "refused", "reason": reason})


def _post(user, account, kind, amount, key, transfer_id=None):
    return LedgerEntry.objects.create(
        account=account, kind=kind, status=LedgerEntry.Status.POSTED,
        amount=amount, balance_after=account.balance, transfer_id=transfer_id,
        initiated_by=user, idempotency_key=key,
    )


def _run_once(user, key, fingerprint, work):
    """Run work() at most once per (user, key).

    The key record, the money movement and the saved response all commit in
    ONE transaction. A second request with the same key waits on the unique
    index until the first finishes, then gets the saved response back.
    """
    with transaction.atomic():
        record, created = IdempotencyRecord.objects.get_or_create(
            user=user, key=key, defaults={"request_hash": fingerprint}
        )
        if not created:
            if record.request_hash != fingerprint:
                return Result(422, {"error": "this Idempotency-Key was used for a different request"})
            return Result(record.response_status, record.response_body, replayed=True)
        result = work()
        record.response_status = result.http_status
        record.response_body = result.body
        record.save(update_fields=["response_status", "response_body"])
        return result


def deposit(user, account_id, amount, key):
    account_id, amount, key = _check_id(account_id), _check_amount(amount), _check_key(key)

    def work():
        account = _lock_accounts(account_id)[account_id]
        if not _may_deposit(user, account):
            return _refuse(user, account, LedgerEntry.Kind.DEPOSIT, amount,
                           "not allowed to deposit into this account", key, 403)
        account.balance += amount
        account.save(update_fields=["balance"])
        entry = _post(user, account, LedgerEntry.Kind.DEPOSIT, amount, key)
        return Result(201, {"status": "posted", "entry_id": entry.id, "balance": account.balance})

    return _run_once(user, key, _fingerprint("deposit", account=account_id, amount=amount), work)


def withdraw(user, account_id, amount, key):
    account_id, amount, key = _check_id(account_id), _check_amount(amount), _check_key(key)

    def work():
        account = _lock_accounts(account_id)[account_id]
        if not _may_debit(user, account):
            return _refuse(user, account, LedgerEntry.Kind.WITHDRAWAL, amount,
                           "not allowed to withdraw from this account", key, 403)
        if account.balance < amount:
            return _refuse(user, account, LedgerEntry.Kind.WITHDRAWAL, amount,
                           "insufficient funds", key, 409)
        account.balance -= amount
        account.save(update_fields=["balance"])
        entry = _post(user, account, LedgerEntry.Kind.WITHDRAWAL, amount, key)
        return Result(201, {"status": "posted", "entry_id": entry.id, "balance": account.balance})

    return _run_once(user, key, _fingerprint("withdraw", account=account_id, amount=amount), work)


def transfer(user, from_id, to_id, amount, key):
    from_id, to_id = _check_id(from_id), _check_id(to_id)
    amount, key = _check_amount(amount), _check_key(key)
    if from_id == to_id:
        raise BadRequest("cannot transfer to the same account")

    def work():
        accounts = _lock_accounts(from_id, to_id)
        source, target = accounts[from_id], accounts[to_id]
        if not _may_debit(user, source):
            return _refuse(user, source, LedgerEntry.Kind.TRANSFER_OUT, amount,
                           "not allowed to transfer from this account", key, 403)
        if source.balance < amount:
            return _refuse(user, source, LedgerEntry.Kind.TRANSFER_OUT, amount,
                           "insufficient funds", key, 409)
        source.balance -= amount
        target.balance += amount
        source.save(update_fields=["balance"])
        target.save(update_fields=["balance"])
        transfer_id = uuid.uuid4()
        _post(user, source, LedgerEntry.Kind.TRANSFER_OUT, amount, key, transfer_id)
        _post(user, target, LedgerEntry.Kind.TRANSFER_IN, amount, key, transfer_id)
        return Result(201, {"status": "posted", "transfer_id": str(transfer_id),
                            "balance": source.balance})

    return _run_once(user, key, _fingerprint("transfer", source=from_id, target=to_id, amount=amount), work)