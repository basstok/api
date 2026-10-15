# Signed change to an internal Message

This small Python 3.10+ example processes one authenticated `content.changed`
reference for one explicitly approved Content item. It checks the Account at a
fixed HTTPS origin, re-reads current Content with a scoped App token, then sends
one actual internal Message to an explicitly approved Chat. It never copies the
Content title or body into the Chat. It accepts no event-supplied URL or destination.

The implementation follows this repository's [published contract](../openapi.json):
the `change` webhook, `GET /api/v1/context`,
`GET /api/v1/contents/{contentId}` and
`POST /api/v1/chats/{chatId}/messages`. It is a reusable handler and a deliberate
one-request CLI, not a hosted webhook service, SDK or readiness certification.

## Try it offline

From the repository root, on Linux or macOS, using only the Python standard library:

```sh
python3 -m unittest discover -s examples -p 'test_*.py' -v
python3 examples/webhook_message.py --help
```

Tests use synthetic references and a fake API. They make no network requests,
read no credentials, activate nothing and send nothing. The CLI refuses to process
events without `--live`; importing the module has no side effects.

## Permissions and deliberate activation

1. Have a human explicitly approve the source Content, destination Chat and the
   wording in `MESSAGE`. A change reference can reveal that activity happened;
   approve that disclosure to the Chat's participants. Do not republish private
   Content text or choose destinations from external input.
2. Use an existing application and a current Member-approved OAuth grant with
   exactly `content:read` and `chat:write`. The grant's selected Labels must admit
   the source Content; the responsible Member must currently be able to read it
   and participate/write in the destination Chat. Scopes do not manufacture access.
   This example uses the responsible Member, with no `actor_id` or persona.
   `chat:read`, `member:write`, moderation and Admin authority are not needed for
   these reads/sends. OAuth setup/PKCE and token rotation are outside this example;
   do not substitute a human session or print tokens.
3. An authorized owner must separately activate a `content.changed` subscription
   using `PUT /api/v1/applications/{applicationId}/webhooks/{webhookId}` and the
   existing grant. That operation accepts the contract's Member or OAuth
   authentication, subject to current application/grant ownership; scopes alone
   do not grant ownership. Supply `grant_id`, `name`, a public HTTPS `endpoint`
   and `events: ["content.changed"]`. The endpoint must resolve entirely to public
   addresses. Securely retain the signing secret returned only by this write;
   listing subscriptions does not recover it. This example performs no activation.
4. Configure an existing HTTPS ingress to call `handle` with the exact raw request
   bytes and uncollapsed header pairs (for example, `list(headers.raw_items())`).
   Enforce body/header limits before buffering, a request deadline and ingress
   concurrency/rate limits. The handler rejects bodies over 16 KiB, duplicate
   headers/JSON keys, invalid signatures, header/payload disagreement, events more
   than five minutes old or in the future, other Accounts and unapproved references.
   Keep a synchronized clock. A valid HMAC authenticates the configured subscription;
   an HTTP `Origin` header is not authentication. The fixed API origin and the
   context Account check bind outbound requests; no webhook URL is ever followed.
5. Keep one persistent private state directory per subscription, on a trusted local
   filesystem. The handler creates it as mode 0700 with mode 0600 receipts. Reuse it
   across invocations and restarts; never put it in Git or clear it to bypass replay
   protection. It serializes requests using a file lock and stops at 1,024 receipts
   without automatic eviction. It is a bounded demonstration, not a production
   queue, long-lived replay store or horizontally scalable receiver.

For deliberate live processing of a privately captured real delivery, provision
`BASSTOK_APP_TOKEN` and `BASSTOK_WEBHOOK_SECRET` securely in the process environment.
Do not paste their values into shell history. `received-body.bin` contains the exact
body bytes; `received-headers.json` is a JSON object containing the three original
`Basstok-Webhook-*` headers. An ingress must reject duplicate headers before saving
that object. The files and state directory belong outside this repository.

```sh
python3 examples/webhook_message.py --live \
  --origin https://account.example \
  --account-id "$APPROVED_ACCOUNT_ID" \
  --content-id "$APPROVED_CONTENT_ID" \
  --chat-id "$APPROVED_CHAT_ID" \
  --body /private/received-body.bin \
  --headers /private/received-headers.json \
  --state-dir /private/webhook-state
```

Replace the reserved example hostname with the exact approved lowercase HTTPS
hostname, without port, path, query or credentials. TLS verification stays enabled;
redirects and environment proxies are disabled so the token is not forwarded.
Context is checked without a token before any authenticated request. API responses
are bounded to 1 MiB and each socket operation has a ten-second timeout. A 401/403,
invalid response or inaccessible resource stops the workflow; no public/anonymous
read fallback is attempted.

## Retries and limits

A fresh lowercase UUIDv4 `Idempotency-Key` is saved and synced **before** sending.
The exact destination, message and input are bound to that receipt. A completed
duplicate returns `duplicate` without another API call. An uncertain send stays
`pending`; inspect it privately and deliberately use `--retry-pending` only with
the same input, configuration and still-fresh delivery. It repeats the same key and
body after rechecking current access. Never generate a new key to resolve an
uncertain send. Changed input with the same delivery ID is rejected. Expired
pending work, capacity exhaustion, lost state or changed configuration requires
manual reconciliation, not deleting receipts or automatically sending again.

An ingress may acknowledge with HTTP 204 only when `handle` returns `sent` or
`duplicate`. Failures must not be turned into success. Arrange bounded error handling
at the ingress; this module neither listens publicly nor retries in the background.
The CLI prints only a short outcome, never response bodies or tokens. It does not
prove live webhook reachability, durable delivery, exactly-once processing under
state loss, external recipient delivery or production readiness. Ordinary Message
acceptance is not a crash-durability guarantee.

This is internal Chat composition. It does not send external email, texts or fax,
place calls, spend communication credit or buy anything. App grants do not permit
the contract's human-only external sending operations. No personal email example
is included, and no live operation is part of the offline checks.
