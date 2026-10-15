from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
import urllib.request
import uuid
from unittest.mock import MagicMock, patch

import webhook_message as example


NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
SECRET = "offline-test-secret"


def signed(event=None):
    event = event or {
        "id": "test-delivery", "event": "content.changed",
        "occurred_at": NOW.isoformat(), "account_id": "test-account",
        "resource": {"type": "Content", "id": "test-content"},
    }
    body = json.dumps(event, separators=(",", ":")).encode()
    prefix = f"v1\n{event['id']}\n{event['occurred_at']}\n".encode()
    signature = hmac.new(SECRET.encode(), prefix + body, hashlib.sha256).hexdigest()
    return body, [
        ("Basstok-Webhook-Id", event["id"]),
        ("Basstok-Webhook-Timestamp", event["occurred_at"]),
        ("Basstok-Webhook-Signature", "v1=" + signature),
    ]


class FakeAPI:
    origin = "https://account.example"

    def __init__(self):
        self.calls = []
        self.account = "test-account"
        self.forbidden = False
        self.uncertain = False

    def request(self, method, path, payload=None, key=None, authenticated=True):
        self.calls.append((method, path, payload, key, authenticated))
        if path == "/api/v1/context":
            return {"account_id": self.account}
        if method == "GET":
            if self.forbidden:
                raise urllib.error.HTTPError(self.origin + path, 403, "Forbidden", {}, None)
            return {"id": "test-content", "body": "Never forward this private text"}
        if self.uncertain:
            raise TimeoutError("Unknown send outcome")
        return {"id": "test-message"}


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / "state"
        self.api = FakeAPI()

    def run_event(self, body=None, headers=None, **options):
        default_body, default_headers = signed()
        return example.handle(
            default_body if body is None else body,
            default_headers if headers is None else headers,
            secret=SECRET, account_id="test-account", content_id="test-content",
            chat_id="approved-chat", api=self.api, state_dir=self.state, now=NOW, **options)

    def changed_event(self, **changes):
        event = json.loads(signed()[0])
        event.update(changes)
        return signed(event)

    def test_authorized_workflow_and_duplicate(self):
        self.assertEqual(self.run_event(), "sent")
        self.assertEqual(self.run_event(), "duplicate")
        self.assertEqual(len(self.api.calls), 3)
        context, reread, send = self.api.calls
        self.assertFalse(context[4])
        self.assertEqual(reread[:2], ("GET", "/api/v1/contents/test-content"))
        self.assertEqual(send[:2], ("POST", "/api/v1/chats/approved-chat/messages"))
        self.assertEqual(send[2], example.MESSAGE)
        self.assertNotIn("private text", json.dumps(send[2]))
        self.assertEqual(uuid.UUID(send[3]).version, 4)
        self.assertEqual((self.state.stat().st_mode & 0o777), 0o700)
        self.assertEqual(((self.state / "receipts.json").stat().st_mode & 0o777), 0o600)

    def test_uncertain_send_requires_explicit_retry_with_identical_key_and_body(self):
        self.api.uncertain = True
        with self.assertRaises(TimeoutError):
            self.run_event()
        first = self.api.calls[-1]
        with self.assertRaisesRegex(ValueError, "retry-pending"):
            self.run_event()
        self.api.uncertain = False
        self.assertEqual(self.run_event(retry_pending=True), "sent")
        self.assertEqual(self.api.calls[-1], first)

    def test_concurrent_duplicate_is_serialized(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda unused: self.run_event(), range(2)))
        self.assertEqual(sorted(results), ["duplicate", "sent"])
        self.assertEqual(len(self.api.calls), 3)

    def test_unauthorized_and_unapproved_events_never_call_api(self):
        body, headers = signed()
        cases = [
            (body + b" ", headers),
            (body, headers[:-1]),
            (body, headers + [headers[0]]),
            self.changed_event(account_id="other-account"),
            self.changed_event(event="chat.changed"),
            self.changed_event(resource={"type": "Content", "id": "other-content"}),
            self.changed_event(occurred_at=(NOW - datetime.timedelta(seconds=301)).isoformat()),
            self.changed_event(occurred_at=(NOW + datetime.timedelta(seconds=301)).isoformat()),
            self.changed_event(body="unexpected body"),
            self.changed_event(actor_id="unexpected-actor"),
        ]
        for case_body, case_headers in cases:
            with self.subTest(body=case_body), self.assertRaises(ValueError):
                self.run_event(case_body, case_headers)
        self.assertEqual(self.api.calls, [])

    def test_input_bounds(self):
        with self.assertRaisesRegex(ValueError, "too large"):
            self.run_event(b" " * (example.MAX_EVENT + 1))
        with self.assertRaises(ValueError):
            self.run_event(headers=[("test", "value")] * 65)
        self.assertEqual(self.api.calls, [])

    def test_duplicate_json_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            example.decode(b'{"account_id":"one","account_id":"two"}')

    def test_valid_signature_with_header_payload_mismatch_is_rejected(self):
        body, headers = signed()
        headers[0] = ("Basstok-Webhook-Id", "different-delivery")
        prefix = f"v1\ndifferent-delivery\n{NOW.isoformat()}\n".encode()
        signature = hmac.new(SECRET.encode(), prefix + body, hashlib.sha256).hexdigest()
        headers[2] = ("Basstok-Webhook-Signature", "v1=" + signature)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            self.run_event(body, headers)
        self.assertEqual(self.api.calls, [])

    def test_wrong_origin_or_tenant_does_not_receive_bearer(self):
        self.api.origin = "https://account.example@other.example"
        with self.assertRaises(ValueError):
            self.run_event()
        self.assertEqual(self.api.calls, [])
        self.api.origin = "https://account.example"
        self.api.account = "other-account"
        with self.assertRaisesRegex(ValueError, "wrong Account"):
            self.run_event()
        self.assertEqual(len(self.api.calls), 1)
        self.assertFalse(self.api.calls[0][4])

    def test_revoked_read_does_not_send(self):
        self.api.forbidden = True
        with self.assertRaises(urllib.error.HTTPError):
            self.run_event()
        self.assertTrue(all(call[0] == "GET" for call in self.api.calls))

    def test_reused_delivery_with_changed_input_rejected(self):
        self.run_event()
        body, headers = self.changed_event(occurred_at=(NOW + datetime.timedelta(seconds=1)).isoformat())
        with self.assertRaisesRegex(ValueError, "changed input"):
            self.run_event(body, headers)
        self.assertEqual(len(self.api.calls), 3)

    def test_full_receipts_fail_closed(self):
        self.state.mkdir(mode=0o700)
        example.save_receipts(self.state, {str(index): {} for index in range(example.MAX_RECEIPTS)})
        with self.assertRaisesRegex(ValueError, "capacity"):
            self.run_event()
        self.assertEqual(self.api.calls, [])


class URLTests(unittest.TestCase):
    def test_origin_is_exact_https_hostname(self):
        self.assertEqual(example.origin_url("https://account.example"), "https://account.example")
        for origin in ["http://account.example", "https://account.example/", "https://account.example?x",
                       "https://account.example#x", "https://account.example:443", "https://USER@account.example",
                       "https://account.example\\other.example", "https://account.example\n"]:
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                example.origin_url(origin)

    def test_redirects_never_forward_token(self):
        api = example.API("https://account.example", "offline-token")
        request = urllib.request.Request("https://account.example/api/v1/contents/test-content",
                                         headers={"Authorization": "Bearer offline-token"})
        with self.assertRaisesRegex(ValueError, "Redirect refused"):
            example.NoRedirect().redirect_request(request, None, 302, "", {}, "https://other.example/")
        self.assertTrue(any(isinstance(handler, example.NoRedirect) for handler in api.opener.handlers))

    def test_request_builds_only_approved_url(self):
        api = example.API("https://account.example", "offline-token")
        with patch.object(api.opener, "open", side_effect=RuntimeError("offline")) as opened:
            with self.assertRaises(RuntimeError):
                api.request("GET", "/api/v1/contents/" + example.urllib.parse.quote("//other.example/?x", safe=""))
            request = opened.call_args.args[0]
            self.assertEqual(request.full_url,
                             "https://account.example/api/v1/contents/%2F%2Fother.example%2F%3Fx")
            self.assertEqual(request.get_header("Authorization"), "Bearer offline-token")
        for path in ["//other.example/", "https://other.example/", "/api/v1/context?redirect=x"]:
            with self.assertRaises(ValueError):
                api.request("GET", path)

    def test_response_bound_is_applied_before_decode(self):
        api = example.API("https://account.example", "offline-token")
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.headers.get_content_type.return_value = "application/json"
        response.headers.get.return_value = "identity"
        response.read.return_value = b" " * (example.MAX_RESPONSE + 1)
        with patch.object(api.opener, "open", return_value=response):
            with self.assertRaisesRegex(ValueError, "response too large"):
                api.request("GET", "/api/v1/context")
        response.read.assert_called_once_with(example.MAX_RESPONSE + 1)

    def test_cli_without_live_flag_never_constructs_api(self):
        arguments = ["webhook_message.py", "--origin", "https://account.example",
                     "--account-id", "test-account", "--content-id", "test-content",
                     "--chat-id", "approved-chat", "--body", "unused-body",
                     "--headers", "unused-headers", "--state-dir", "unused-state"]
        with patch("sys.argv", arguments), patch.object(example, "API") as api:
            with patch("sys.stderr"):
                self.assertEqual(example.main(), 1)
        api.assert_not_called()


class ContractTests(unittest.TestCase):
    def test_used_operations_permissions_and_signature_contract(self):
        spec = json.loads((Path(__file__).resolve().parents[1] / "openapi.json").read_text())
        self.assertIn({"oauth": ["content:read"]},
                      spec["paths"]["/api/v1/contents/{contentId}"]["get"]["security"])
        send = spec["paths"]["/api/v1/chats/{chatId}/messages"]["post"]
        self.assertIn({"oauth": ["chat:write"]}, send["security"])
        self.assertIn({"$ref": "#/components/parameters/IdempotencyKey"}, send["parameters"])
        pattern = spec["components"]["parameters"]["IdempotencyKey"]["schema"]["pattern"]
        self.assertRegex(str(uuid.uuid4()), pattern)
        webhook = spec["webhooks"]["change"]["post"]
        self.assertEqual({parameter["name"] for parameter in webhook["parameters"]}, {
            "Basstok-Webhook-Id", "Basstok-Webhook-Timestamp", "Basstok-Webhook-Signature"})
        self.assertIn("content.changed", spec["components"]["schemas"]["WebhookPayload"]
                      ["properties"]["event"]["enum"])


if __name__ == "__main__":
    unittest.main()
