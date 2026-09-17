"""Atomic monthly usage and server-managed entitlements. No resume storage."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import re
import uuid


class QuotaUnavailable(Exception):
    pass


class QuotaExhausted(Exception):
    pass


@dataclass(frozen=True)
class Actor:
    kind: str
    key: str
    email: str = ""


@dataclass(frozen=True)
class Allowance:
    plan: str
    limit: int
    used: int
    month: str

    @property
    def remaining(self):
        return max(0, self.limit - self.used)


@dataclass(frozen=True)
class Reservation:
    request_id: str
    actor_key: str
    month: str


def user_actor(identity):
    return Actor("user", hashlib.sha256(identity["owner"].encode()).hexdigest(), identity["email"])


def mint_guest_token(secret):
    _valid_secret(secret)
    body = "v1." + uuid.uuid4().hex
    signature = hmac.new(secret.encode(), ("guest:" + body).encode(), hashlib.sha256).hexdigest()
    return body + "." + signature


def guest_actor(token, secret):
    _valid_secret(secret)
    if not isinstance(token, str) or not re.fullmatch(r"v1\.[a-f0-9]{32}\.[a-f0-9]{64}", token):
        raise QuotaUnavailable("Invalid browser identity")
    body, signature = token.rsplit(".", 1)
    expected = hmac.new(secret.encode(), ("guest:" + body).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise QuotaUnavailable("Invalid browser identity")
    return Actor("guest", hashlib.sha256(("guest:" + body).encode()).hexdigest())


def _valid_secret(secret):
    if not isinstance(secret, str) or len(secret) < 32 or secret.startswith("REPLACE_"):
        raise QuotaUnavailable("Browser signing is not configured")


def _utc(now):
    if now.tzinfo is None:
        raise ValueError("Server time must be timezone-aware")
    return now.astimezone(timezone.utc)


def _plan(actor, entitlement, now):
    if actor.kind == "guest":
        return "Guest", 3
    if actor.kind != "user":
        raise QuotaUnavailable("Invalid actor")
    expiry = entitlement.get("expires_at")
    limit = entitlement.get("monthly_limit")
    if (entitlement.get("active") is True and entitlement.get("payment_verified") is True
            and isinstance(expiry, datetime) and expiry.tzinfo is not None and expiry > now
            and type(limit) is int and limit > 10):
        return "Paid", limit
    return "Free", 10


def _used(record):
    value = record.get("used", 0)
    if type(value) is not int or value < 0:
        raise QuotaUnavailable("Usage needs review")
    return value


class MonthlyQuota:
    """Store.atomic must execute its callback as one serializable transaction."""

    def __init__(self, store):
        self.store = store

    def _status(self, tx, actor, now):
        month = now.strftime("%Y-%m")
        entitlement = tx.read("analysis_entitlements", actor.key) if actor.kind == "user" else {}
        plan, limit = _plan(actor, entitlement, now)
        record = tx.read("analysis_usage", actor.key + "_" + month)
        return Allowance(plan, limit, _used(record), month)

    def status(self, actor, now=None):
        now = _utc(now or datetime.now(timezone.utc))
        return self.store.atomic(lambda tx: self._status(tx, actor, now))

    def reserve(self, actor, now=None, request_id=None):
        now = _utc(now or datetime.now(timezone.utc))
        request_id = request_id or uuid.uuid4().hex

        def operation(tx):
            allowance = self._status(tx, actor, now)
            ledger = tx.read("analysis_requests", request_id)
            if ledger:
                if ledger.get("actor_key") != actor.key or ledger.get("month") != allowance.month:
                    raise QuotaUnavailable("Request ownership mismatch")
                # A duplicate must not send another model call, even if already paid for.
                raise QuotaUnavailable("Request already submitted")
            if allowance.remaining == 0:
                raise QuotaExhausted("Monthly allowance used")
            tx.write("analysis_usage", actor.key + "_" + allowance.month, {
                "used": allowance.used + 1, "kind": actor.kind,
                "month": allowance.month, "email": actor.email, "updated_at": now,
            })
            tx.write("analysis_requests", request_id, {
                "actor_key": actor.key, "month": allowance.month,
                "status": "reserved", "created_at": now,
            })
            return Reservation(request_id, actor.key, allowance.month)

        return self.store.atomic(operation)

    def finish(self, reservation, success):
        """A failed generation refunds once, in its ORIGINAL monthly bucket."""
        def operation(tx):
            ledger = tx.read("analysis_requests", reservation.request_id)
            usage_id = reservation.actor_key + "_" + reservation.month
            usage = tx.read("analysis_usage", usage_id)
            if (ledger.get("actor_key") != reservation.actor_key
                    or ledger.get("month") != reservation.month):
                raise QuotaUnavailable("Request ownership mismatch")
            if ledger.get("status") != "reserved":
                return
            count = _used(usage)
            if not success:
                if count < 1:
                    raise QuotaUnavailable("Usage needs review")
                tx.write("analysis_usage", usage_id, {**usage, "used": count - 1})
            tx.write("analysis_requests", reservation.request_id, {
                **ledger, "status": "completed" if success else "failed",
                "finished_at": datetime.now(timezone.utc),
            })
        self.store.atomic(operation)


class FirestoreStore:
    def __init__(self, client, firestore_module):
        self.client = client
        self.firestore = firestore_module

    def atomic(self, operation):
        client = self.client

        class Transaction:
            def __init__(self, transaction):
                self.transaction = transaction

            def read(self, collection, key):
                reference = client.collection(collection).document(key)
                return reference.get(transaction=self.transaction).to_dict() or {}

            def write(self, collection, key, values):
                self.transaction.set(client.collection(collection).document(key), values)

        @self.firestore.transactional
        def run(transaction):
            return operation(Transaction(transaction))

        try:
            return run(client.transaction())
        except (QuotaUnavailable, QuotaExhausted):
            raise
        except Exception as error:
            raise QuotaUnavailable("Usage service unavailable") from error
