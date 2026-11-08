from django.test import TransactionTestCase
from django.urls import reverse
from ledger.models import User, Account, LedgerEntry

class LedgerTestCase(TransactionTestCase):
    def setUp(self):
        # Create users for each role
        self.admin = User.objects.create_superuser(username="adminuser", password="password123", role=User.Role.ADMIN)
        self.holder = User.objects.create_user(username="holderuser", password="password123", role=User.Role.HOLDER)
        
        # Create an account for the holder with 1000 paise (₹10)
        self.account = Account.objects.create(owner=self.holder, name="Main Savings", balance=1000)

    def test_deposit_idempotency(self):
        self.client.login(username="adminuser", password="password123")
        url = reverse("api_deposit")
        payload = {"account_id": self.account.id, "amount": 500}
        headers = {"HTTP_IDEMPOTENCY_KEY": "unique-dep-key-1"}
        
        # First request
        res1 = self.client.post(url, payload, content_type="application/json", **headers)
        self.assertEqual(res1.status_code, 201)
        
        # Second request with the SAME idempotency key (should return success but NOT add money twice)
        res2 = self.client.post(url, payload, content_type="application/json", **headers)
        self.assertEqual(res2.status_code, 201)
        
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 1500) # 1000 initial + 500 once

    def test_insufficient_funds_refusal(self):
        self.client.login(username="holderuser", password="password123")
        url = reverse("api_withdraw")
        payload = {"account_id": self.account.id, "amount": 5000} # More than balance (1000)
        headers = {"HTTP_IDEMPOTENCY_KEY": "unique-withdraw-key-1"}
        
        res = self.client.post(url, payload, content_type="application/json", **headers)
        self.assertEqual(res.status_code, 409) # Conflict / insufficient funds
        
        # Verify refusal was logged in the ledger
        entry = LedgerEntry.objects.filter(account=self.account).latest("created_at")
        self.assertEqual(entry.status, LedgerEntry.Status.REFUSED)
        self.assertEqual(entry.reason, "insufficient funds")

# Create your tests here.
