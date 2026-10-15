#!/usr/bin/env python3
"""Process one signed Content reference; see README.md before live use."""

import argparse
import datetime
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid


MAX_EVENT = 16_384
MAX_RESPONSE = 1_048_576
MAX_RECEIPTS = 1024
MAX_AGE = 300
MESSAGE = {"body": "A selected Content item changed. Please review it in Basstok."}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)


def identifier(value):
    require(isinstance(value, str) and 1 <= len(value) <= 256, "Invalid reference")
    require(value not in (".", "..") and all(ord(char) >= 32 for char in value),
            "Invalid reference")
    return value


def origin_url(origin):
    require(isinstance(origin, str) and len(origin) <= 253, "Invalid HTTPS origin")
    require(re.fullmatch(r"https://[a-z0-9]+(?:[.-][a-z0-9]+)*", origin),
            "Use an exact lowercase HTTPS hostname, without path or port")
    return origin


def verify(body, header_pairs, secret, account_id, content_id, now):
    require(len(body) <= MAX_EVENT, "Webhook too large")
    require(isinstance(secret, str) and 1 <= len(secret) <= 4096, "Missing signing secret")
    headers = {}
    require(len(header_pairs) <= 64, "Too many headers")
    for name, value in header_pairs:
        require(isinstance(name, str) and isinstance(value, str), "Invalid header")
        require(len(name) <= 128 and len(value) <= 1024, "Header too large")
        key = name.lower()
        require(key not in headers, "Duplicate header")
        headers[key] = value
    delivery = identifier(headers.get("basstok-webhook-id"))
    timestamp = headers.get("basstok-webhook-timestamp", "")
    signature = headers.get("basstok-webhook-signature", "")
    require(re.fullmatch(r"v1=[0-9a-f]{64}", signature), "Invalid signature")
    signed = b"v1\n" + delivery.encode() + b"\n" + timestamp.encode() + b"\n" + body
    expected = "v1=" + hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    require(hmac.compare_digest(signature, expected), "Invalid signature")
    occurred = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    require(occurred.tzinfo is not None and abs((now - occurred).total_seconds()) <= MAX_AGE,
            "Stale or future webhook")
    event = decode(body)
    require(isinstance(event, dict) and set(event) == {
        "id", "event", "occurred_at", "account_id", "resource"}, "Unexpected webhook fields")
    require(event["id"] == delivery and event["occurred_at"] == timestamp,
            "Header/payload mismatch")
    require(event["account_id"] == account_id, "Wrong Account")
    require(event["event"] == "content.changed", "Unsupported event")
    resource = event["resource"]
    require(isinstance(resource, dict) and set(resource) == {"type", "id"},
            "Invalid resource")
    require(resource["type"] == "Content" and resource["id"] == content_id,
            "Unapproved resource")
    return delivery


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise ValueError("Redirect refused")


class API:
    def __init__(self, origin, token):
        self.origin = origin_url(origin)
        require(isinstance(token, str) and 1 <= len(token) <= 8192
                and all(33 <= ord(char) <= 126 for char in token), "Invalid App token")
        self.token = token
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, method, path, payload=None, key=None, authenticated=True):
        require(path.startswith("/api/v1/") and not any(char in path for char in "?#\\"),
                "Invalid API path")
        headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
        if authenticated:
            headers["Authorization"] = "Bearer " + self.token
        if key:
            headers["Idempotency-Key"] = key
        data = None
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.origin + path, data, headers, method=method)
        with self.opener.open(request, timeout=10) as response:
            require(response.status == 200, "Unexpected API status")
            require(response.headers.get_content_type() == "application/json",
                    "Expected JSON response")
            require(response.headers.get("Content-Encoding", "identity") == "identity",
                    "Unexpected response encoding")
            raw = response.read(MAX_RESPONSE + 1)
        require(len(raw) <= MAX_RESPONSE, "API response too large")
        result = decode(raw)
        require(isinstance(result, dict), "Expected API object")
        return result


def save_receipts(directory, receipts):
    descriptor, temporary = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(descriptor, "w") as output:
            json.dump(receipts, output, separators=(",", ":"))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, directory / "receipts.json")
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def handle(body, headers, *, secret, account_id, content_id, chat_id, api,
           state_dir, retry_pending=False, now=None):
    """Ingress adapter: pass exact body bytes and uncollapsed header pairs.

    A successful return can be acknowledged with HTTP 204. Errors must not be
    acknowledged as success. Calls are serialized across this private directory.
    """
    origin_url(api.origin)
    for value in (account_id, content_id, chat_id):
        identifier(value)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    delivery = verify(body, headers, secret, account_id, content_id, now)
    state_dir = Path(state_dir)
    state_dir.mkdir(mode=0o700, parents=False, exist_ok=True)
    mode = state_dir.lstat()
    require(stat.S_ISDIR(mode.st_mode) and mode.st_uid == os.getuid()
            and stat.S_IMODE(mode.st_mode) == 0o700, "State directory must be private (0700)")
    lock_fd = os.open(state_dir / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, "r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        receipt_path = state_dir / "receipts.json"
        receipts = {}
        if receipt_path.exists():
            with receipt_path.open("rb") as source:
                raw = source.read(MAX_RESPONSE + 1)
            require(len(raw) <= MAX_RESPONSE, "Receipt file too large")
            receipts = decode(raw)
            require(isinstance(receipts, dict) and len(receipts) <= MAX_RECEIPTS,
                    "Invalid receipts")
        receipt_id = hashlib.sha256(delivery.encode()).hexdigest()
        binding = hashlib.sha256(json.dumps(
            [api.origin, account_id, content_id, chat_id, MESSAGE, body.hex()],
            separators=(",", ":")).encode()).hexdigest()
        receipt = receipts.get(receipt_id)
        if receipt:
            require(receipt["binding"] == binding, "Delivery reused with changed input")
            if receipt["status"] == "done":
                return "duplicate"
            require(receipt["status"] == "pending" and retry_pending,
                    "Uncertain prior attempt; deliberate --retry-pending required")
        else:
            require(len(receipts) < MAX_RECEIPTS, "Receipt capacity reached; reconcile manually")
        context = api.request("GET", "/api/v1/context", authenticated=False)
        require(context.get("account_id") == account_id, "Origin serves the wrong Account")
        current = api.request("GET", "/api/v1/contents/" + urllib.parse.quote(content_id, safe=""))
        require(current.get("id") == content_id, "Resource identity mismatch")
        if receipt is None:
            receipt = {"binding": binding, "status": "pending", "key": str(uuid.uuid4())}
            receipts[receipt_id] = receipt
            save_receipts(state_dir, receipts)
        result = api.request("POST", "/api/v1/chats/" + urllib.parse.quote(chat_id, safe="")
                             + "/messages", MESSAGE, receipt["key"])
        identifier(result.get("id"))
        receipt["status"] = "done"
        save_receipts(state_dir, receipts)
        return "sent"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Permit one internal Message operation")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--body", type=Path, required=True, help="Exact received bytes")
    parser.add_argument("--headers", type=Path, required=True, help="JSON object of received headers")
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--retry-pending", action="store_true")
    args = parser.parse_args()
    try:
        require(args.live, "Offline by default; use the offline tests or deliberately pass --live")
        with args.body.open("rb") as source:
            body = source.read(MAX_EVENT + 1)
        with args.headers.open("rb") as source:
            raw = source.read(MAX_EVENT + 1)
        require(len(raw) <= MAX_EVENT, "Headers too large")
        headers = decode(raw)
        require(isinstance(headers, dict), "Expected header object")
        result = handle(body, list(headers.items()), secret=os.environ.get("BASSTOK_WEBHOOK_SECRET", ""),
                        account_id=args.account_id, content_id=args.content_id, chat_id=args.chat_id,
                        api=API(args.origin, os.environ.get("BASSTOK_APP_TOKEN", "")),
                        state_dir=args.state_dir, retry_pending=args.retry_pending)
        print(result)
        return 0
    except Exception:
        print("Refused or uncertain operation; no automatic retry. Check private ingress/state.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
