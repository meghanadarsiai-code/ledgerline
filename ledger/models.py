from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        HOLDER = "holder", "Account holder"
        AUDITOR = "auditor", "Auditor (read-only)"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.HOLDER)


class Account(models.Model):
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="accounts")
    name = models.CharField(max_length=100)
    balance = models.BigIntegerField(default=0)  # in paise, never floats
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(balance__gte=0), name="balance_never_negative"),
        ]


class LedgerEntry(models.Model):
    class Kind(models.TextChoices):
        DEPOSIT = "deposit"
        WITHDRAWAL = "withdrawal"
        TRANSFER_OUT = "transfer_out"
        TRANSFER_IN = "transfer_in"

    class Status(models.TextChoices):
        POSTED = "posted"
        REFUSED = "refused"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="entries")
    kind = models.CharField(max_length=15, choices=Kind.choices)
    status = models.CharField(max_length=10, choices=Status.choices)
    amount = models.BigIntegerField()  # always positive; kind gives the direction
    balance_after = models.BigIntegerField(null=True)  # empty for refused attempts
    transfer_id = models.UUIDField(null=True, blank=True)  # shared by both halves of a transfer
    initiated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    idempotency_key = models.CharField(max_length=100, blank=True)
    reason = models.CharField(max_length=200, blank=True)  # why it was refused
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="entry_amount_positive"),
        ]


class IdempotencyRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    key = models.CharField(max_length=100)
    request_hash = models.CharField(max_length=64)  # fingerprint of the request
    response_status = models.IntegerField(null=True)
    response_body = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "key"], name="one_key_per_user"),
        ]

# Create your models here.
