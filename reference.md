# Basstok REST API reference

The Basstok REST API supports signed-in clients and delegated Agents. The
[complete OpenAPI contract](openapi.json) describes every published operation,
request, response, and authentication requirement. Each community also serves
the contract for its installed release at:

```text
https://<community>/openapi.json
```

Requests and responses use JSON unless noted otherwise. Always use the target
community's HTTPS origin, not a shared API hostname.

Send `Accept-Language` with the user's language preference for Basstok-owned
presentation text, such as official Agent names and permission explanations.
English is the fallback; German, Spanish, French, Portuguese, Japanese,
Chinese and Arabic are available. Resource IDs, enum values, scopes and
Member-authored text do not change with the language. Public Website
declarations may include explicitly authored translations using the same
routes; the shapes and bounds are in OpenAPI.

Ordinary HTTP clients negotiate response compression automatically. Eligible
text responses support gzip and Zstandard; always respect the returned
`Content-Encoding`, cache policy and validators. Files retain their ordinary
authorized delivery and conditional-request behavior.

[Authentication](#member-sessions) · [Permissions](#authorization-model)
· [OAuth](#oauth) · [Webhooks](#webhook-registration)
· [Scheduling](#schedule-requests) · [Official Agents](#manage-official-agents) · [Errors](#errors)

## Member sessions

Signed-in clients use a Member session as a bearer token. Agents use the
separate [OAuth flow](#oauth); never give an Agent a human Member's session.

The email sign-in endpoints are `POST /api/v1/auth/magic-link` and
`POST /api/v1/auth/magic-link/complete`. The first accepts an email address
and returns `202` when the request is accepted. Completion uses the one-time
code and a client-generated secure `session_token`; the exact JSON schemas
are in [OpenAPI](openapi.json). Keep authentication codes and sessions private.
Email delivery must be available for this sign-in flow.

Use `GET /api/v1/auth/session` to identify the current Member and
`DELETE /api/v1/auth/session` to revoke the current Member session.
Account safety, Terms acceptance, blocking, and deliberate account deletion
have separate task-shaped endpoints under `/api/v1/account`.

A Member session does not bypass resource authorization. Private Chat access
requires participation, including the Member's admission boundary. Management
operations require the Member's current authority.

## Client operations

The full contract includes capabilities beyond delegated Agent scopes:

- **Community and publishing:** `/api/v1/context`, `/api/v1/organization`,
  `/api/v1/contents`, `/api/v1/labels`, `/api/v1/routes`, and `/api/v1/site`.
- **Members and connections:** `/api/v1/members` and `/api/v1/member-connections`.
- **Messages and files:** `/api/v1/chats`, its Message endpoints, and
  `/api/v1/assets`, including bounded multipart uploads.
- **Participation:** reactions, subscriptions, Search, notifications, push
  registrations, and foreground events.
- **Calls:** `/api/v1/calls`, participant signaling, recording consent, and
  the authorized recording-upload operations.
- **Management and imports:** official Agent installation, application grants,
  safety reports, and `/api/v1/imports`.

Use each OpenAPI operation's `security` requirement. Some operations accept
only Member sessions; an OAuth token cannot use them merely because the
endpoint is public documentation. Imports require the current responsible
human Manager and do not grant private Chat reading rights.

For an Administration screen, `GET /api/v1/organization/management` returns
the community's `id`, `name`, and `system_labels` only while the signed-in
Member has Manager authority. It returns `403` when that authority is absent
or revoked. Rename the community with `PUT /api/v1/organization`; change its
audience with `PUT /api/v1/organization/audience`. These operations require a
Member session, not an Agent token. Every mutation checks current authority.

### Manage appearance, homepage and Members

Use `PUT /api/v1/organization/appearance` with `{"primary_color":"blue"}`
to select the website color. Choose `rose`, `orange`, `amber`, `lime`,
`emerald`, `cyan`, `blue`, `violet` or `fuchsia`; omit the value or use `null`
to restore the default. This requires a current human Manager session.

Read the editable homepage with `GET /api/v1/organization/homepage`. Save its
title and Markdown body with `PUT /api/v1/organization/homepage`, echoing the
returned `version`. An exact retry is safe; a stale edit returns `409`.
This is also Manager-only and leaves other pages and posts unchanged.

`GET /api/v1/members?q=Mara` filters authorized Members by display name.
The optional filter is limited to 256 UTF-8 bytes and matches substrings with
ASCII case folding. Follow `next_offset` with the same query and authorization;
a short page may still have a continuation. The offset is not a Member count.
The existing session, scope and resource-access requirements still apply.

### Find or create a Basstok

On `basstok.com`, `GET /api/v1/basstoks?hostname=your-name` checks one exact
name, not a directory. `POST /api/v1/basstoks` starts email verification;
`POST /api/v1/basstoks/complete` completes the verified claim. Open the returned
`sign_in_url` to sign in on the new hostname. Sessions remain separate by
origin. The [OpenAPI contract](openapi.json) specifies the verification and
completion tokens to retain for a safe retry.

### Connect a domain

A Manager can connect a custom hostname to the same Basstok, without creating
another community. The permanent Basstok address remains available. These
operations require a current human Manager session; Agent tokens cannot use
them. Check the target's `/openapi.json` for availability in its installed release.

First add the hostname:

```http
POST /api/v1/organization/domains
Authorization: Bearer <manager-session>
Content-Type: application/json

{"hostname":"community.example.com"}
```

The response contains `permanent_origin` and a `domains` array. Each domain has
an `id`, `hostname`, `state` (`pending` or `active`), `verification_record` and
`verification_value`. An identical add returns the same request. A pending
request does not activate the hostname or reserve it exclusively.

In your DNS settings:

1. Point the hostname to your permanent Basstok address. Use a CNAME for a
   subdomain, or your provider's apex ALIAS/ANAME equivalent or matching A/AAAA
   records for a root domain.
2. Add the returned TXT record and value to confirm domain ownership.
3. Send `POST /api/v1/organization/domains/{domainId}/verify` with no body.

Basstok verifies DNS and provisions HTTPS before connecting the domain. Every
resolved address must be public and match the permanent address. Basstok does
not change DNS. If DNS is not ready, the response remains `pending`; repeat
verification after correcting it. DNS or HTTPS failures preserve the request.
Only one Basstok can have an active attachment for a hostname.

Read current requests with `GET /api/v1/organization/domains`. To remove one,
send `DELETE /api/v1/organization/domains/{domainId}` with no body. Successful
removal stops routing through that hostname without changing the permanent
address or community data. Switch to `permanent_origin` and sign in there;
browser sessions are not shared between hostnames.

There may be up to four saved domain requests per Basstok. Supply an ASCII
hostname, including punycode where needed, of at most 244 bytes. Do not include
a scheme, path, port, wildcard or IP address. Basstok-provided names cannot be
claimed as custom domains. Case and one trailing dot normalize automatically.

These operations return `200` with the current domain list. Invalid input
returns `400`, missing or invalid authentication `401`, insufficient current
Manager authority `403`, an unavailable request `404`, and a conflicting
attachment or request limit `409`. Temporary failures return `503`.

After an uncertain response, read current state and retry the same operation.
An unsuccessful response does not prove that nothing changed. Repeat
verification even if the request already reports `active` to finish connecting
it. An uncertain removal withholds routing; retry removal on the permanent
hostname. Removal uses the request ID, so retrying an old removal cannot delete
a newly added attachment.

### Use your mail server

Managers can connect a community's existing SMTP service from Administration
→ Community email on Web, iPhone/iPad or Android. The same operations are
available to other clients through a current human Member session, not an
Agent token:

- `GET /api/v1/organization/email` reads the selected sender, host, port and
  TLS mode. An absent `smtp` field means the default mail service is selected.
- `POST /api/v1/organization/email/verify` checks supplied settings without
  changing delivery, retaining credentials or sending an email.
- `PUT /api/v1/organization/email` checks and selects the supplied connection.

Both writes accept this shape; supply your own credentials securely:

```json
{
  "endpoint": {
    "sender": "hello@community.example",
    "host": "smtp.community.example",
    "port": 465,
    "security": "implicit_tls"
  },
  "credentials": {
    "username": "your-smtp-username",
    "password": "your-smtp-password"
  }
}
```

Use `implicit_tls` for TLS from connection establishment or `starttls` for
mandatory TLS upgrade before authentication. The server must be reachable at
a public DNS hostname with a valid matching certificate. JSON is limited to
4 KiB. Credentials are write-only and never appear in a response.

A successful check returns `{"verified": true}`. It does not activate the
connection. Saving returns the selected `smtp` endpoint without credentials;
future community email uses that connection. There is no fallback to another
provider on delivery failure. Member preferences and Basstok unsubscribe
behavior still apply automatically.

Each operation requires current Manager authority, including after a network
check. Invalid input returns `400`, an invalid session `401`, insufficient
authority `403`, a concurrent update/check limit `409`, and an unsuccessful
check or save `502`. Errors do not echo credentials. A failed check leaves
delivery unchanged. After an uncertain save response, read settings or repeat
the exact request; an exact retry does not create another connection.

### Connect your storage

Managers can inspect `GET /api/v1/organization/storage` or check a candidate
bucket with `POST /api/v1/organization/storage/verify`. Both require a human
Member session; delegated Agent tokens are not accepted.

The check accepts `target` (HTTPS endpoint, region and bucket) and private
`credentials`, as specified in OpenAPI. It tests the required S3 operations
with temporary objects and uploads, then removes them. Success returns
`{"verified": true}`. Credentials are neither returned nor retained.

Checking does not connect the bucket, move data or change the community's
current storage. A different target must be empty and dedicated to the
community. Customer lifecycle and browser CORS settings are separate;
[see the bucket requirements](https://github.com/basstok/storage).

Invalid settings return `400`; an invalid or revoked session returns `401`,
and missing current Manager authority returns `403`. A failed bucket check
returns `502` without echoing credentials or provider diagnostics.

To move a managed community, separately confirm the action with the Manager
and send the same connection input to
`POST /api/v1/organization/storage/activate`. A `202` response means the move
has started, not that it has finished. Community activity pauses during the
move; unfinished uploads may need to be started again. Closing the client
does not stop an admitted move. Connection credentials are retained privately
for ongoing storage access, never returned by the API.

Read `GET /api/v1/organization/storage` for `custody`: `managed`,
`transferring` or `customer_owned`. During a move, `target` identifies the
selected bucket and `transfer` reports `objects_copied` and `bytes_copied`.
These counters are not a completion percentage.

An interrupted move can resume with `POST /api/v1/organization/storage/resume`
and an empty body. An exact activation retry is safe; a different connection
returns `409`. Read status before retrying an uncertain response. Activation
does not replace an already connected customer bucket. These operations
require current human Manager authority; no Agent scope grants them.

The following operation tables show **Agent scopes**. Signed-in clients use
their Member session and ordinary resource permissions, as specified by
OpenAPI. Neither authentication method creates authority beyond its current
Member and resource context.

## Authorization model

Agents have no resource access by default. A request is authorized only when
all of these remain true:

- the access token has the required scope;
- the current application grant includes that scope;
- the Member who authorized the grant can still perform the operation.

Ordinary object-level authorization is always evaluated as well. Content must
carry an ordinary Label selected for the grant. Chat and Message access instead
require the effective Member to be a participant in that exact Chat. The
effective Member is the responsible human by default, or an explicitly selected
no-login persona created and still controlled by the same application for that
human. Knowing a resource ID does not bypass either boundary.

The effective Member contributes resource context, not authority. Selecting a
persona never adds its Labels or privileges to the grant: the responsible
human's current account and authority remain the ceiling for the request.

Changing or removing any part of that intersection affects subsequent REST
requests, event streams, and webhook delivery. Demoting or deleting the
responsible Member also removes authority immediately. An unavailable object
and an object outside the grant are reported without exposing the object's
contents.

### Public Agent scopes

| Scope | Permits |
|---|---|
| `content:read` | Read Content, Comments, Labels, and Content-owned Assets; receive `content.changed` |
| `content:write` | Create selected-Label Content and, with the responsible Member's current moderation authority, replace already-published selected-Label Content; includes pending draft Assets |
| `engagement:write` | React to and subscribe to selected Content, when combined with `content:read` |
| `member:read` | Read and search bounded Member presentations available to the responsible Member; receive authorized `member.created` references |
| `member:write` | Create no-login persona Members and perform Manager-authorized Member mutations |
| `chat:read` | Read the effective Member's participant Chats, Messages, Chat Assets, and scoped events; receive authorized `chat.changed` references |
| `chat:write` | Create Chats, add participants, send Messages, signal typing, and add Chat-owned Assets where the effective Member may do so |
| `moderation:write` | Use task-shaped Content and Comment moderation operations |

Scopes do not imply one another. A write-only operation may return only the
resource ID rather than disclosing the updated representation. In particular,
`content:write` can create selected-Label Content without granting read access.
Replacing already-published Content additionally requires the responsible
Member's current ordinary moderation authority; `moderation:write` alone can
use only the task-shaped moderation operations and cannot replace a body or
Labels. `chat:write` can create or change an authorized Chat without granting
Chat or Message reads. Read scopes likewise do not permit writes.
Request only the scopes an Agent needs.

### Create identities and safe retries

Basstok assigns canonical IDs for Chat, Message, and Asset creates. These
requests require an `Idempotency-Key` header containing a lowercase RFC 4122
UUIDv4:

- `POST /api/v1/chats`;
- `POST /api/v1/chats/{chatId}/messages`;
- `POST /api/v1/assets`;
- `POST /api/v1/content-drafts/{contentId}/assets`;
- `POST /api/v1/assets/uploads`.

The key identifies one logical create attempt; it is not the new resource ID.
An exact retry with the same key and request returns the same result. Reusing
the key for a changed create conflicts instead of creating or replacing
another resource. Keep the key and request stable after an ambiguous outcome,
then use the canonical ID returned by Basstok for subsequent operations. Use a
new key for a new logical create.

Missing or malformed keys return `400`. Reusing a key for a different create
returns `409`. Chat, Message, and small-Asset creates return `200`; multipart
upload admission returns `201` with both its server-assigned upload ID and
Asset ID.

### Select resources

The responsible Member selects ordinary Labels for a grant with:

```http
PUT /api/v1/application-grants/{grantId}/resources
Authorization: Bearer <member-session>
Content-Type: application/json

{
  "content_label_ids": ["favorites"]
}
```

This is a Member authorization operation, not an Agent-token operation. It
replaces the complete Content selection. An empty array removes the grant's
Content access immediately; it does not grant or remove participant-scoped Chat
access.

## Schedule requests

Submit future API mutations once. Basstok executes them at or after their due
times even when the Agent is offline. No webhook receiver or new scope is
required. Check the community's `/openapi.json` for support in its installed
release.

For example, schedule publication of a draft already created by this
delegation, using `content:write`:

```http
PUT /api/v1/schedules/ca681d22-75f0-4aa2-a82d-3528318ab433
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "requests": [
    {
      "execute_at": "2027-01-01T09:00:00Z",
      "request": {
        "method": "POST",
        "path": "/api/v1/content-drafts/75b4ea59-0f50-49f4-9e14-b6149f4a4493/publish"
      }
    }
  ]
}
```

Choose a fresh lowercase UUIDv4 for the batch and retain it for retries.
`200` returns the accepted requests and current progress. An identical retry
returns that progress without creating another schedule.

### Supported mutations

Each request keeps its ordinary endpoint's body and authorization:

| Request | Required Agent scopes |
|---|---|
| `PUT /api/v1/member-creations/{memberId}` | `member:write` |
| `PUT /api/v1/content-drafts/{contentId}` | `content:write` |
| `POST /api/v1/content-drafts/{contentId}/publish` | `content:write` |
| `PUT /api/v1/contents/{contentId}/comment-creations/{commentId}` | `content:read` + `content:write` |
| `POST /api/v1/chats` | `chat:write` |
| `POST /api/v1/chats/{chatId}/messages` | `chat:write` |

Put the normal JSON body in `request.body`; omit it for draft publication.
Chat and Message creation require `request.idempotency_key`, which supplies
their ordinary `Idempotency-Key` header. Other supported operations use their
existing path identity. Keep both identities and requests unchanged when
retrying an uncertain outcome.

Paths cannot include a hostname, query parameters or arbitrary headers. There
are no placeholders or dependencies: create a Chat first and use its returned
ID when scheduling Messages. Reactions, subscriptions, edits, moderation and
other mutations remain immediate-only.

### Timing and current permissions

Use UTC `YYYY-MM-DDTHH:MM:SSZ` in nondecreasing order. New requests cannot
predate the current UTC second. There is **no application-defined future
scheduling horizon**; the timestamp format uses four-digit years through 9999.
Equal-time requests execute in their listed order. An earlier retry delays
later items in that batch. A terminal failure is recorded and the next item
proceeds; successful work is not rolled back.

Every execution rechecks the current grant, responsible Member, controlled
persona and resource access. Submission does not preserve permissions that
are later removed, and unrelated permission additions do not invalidate work.
Access-token expiry alone does not cancel accepted work; revoking the grant
prevents subsequent authorized execution. A human session cannot submit an
Agent schedule, and another grant cannot inspect or control it.

### Inspect and change a schedule

- `GET /api/v1/schedules/{scheduleId}` returns requests, ordered `results`,
  `attempts` for the next item, and any `retry_at`, `paused_at`, `completed_at`
  or `cancelled_at` timestamp. A result has an HTTP `status` and an optional
  `resource_id`, not a resource body. Responses are `no-store`.
- `POST /api/v1/schedules/{scheduleId}/pause` durably pauses pending work.
  An already admitted request may finish. Refresh progress before editing.
- While paused, repeat `PUT` with the same batch ID to correct its unattempted
  tail. Preserve the completed prefix and any attempted next request exactly,
  including times: an uncertain attempt may already have committed. Remaining
  requests must be future-dated and ordered. Invalid changes leave the old
  batch intact; accepted changes keep it paused.
- `POST /api/v1/schedules/{scheduleId}/resume` resumes overdue work in order
  without resetting attempts. Pause and resume return `200` with progress.
- `DELETE /api/v1/schedules/{scheduleId}` cancels pending work and returns
  `204`. Cancellation cannot undo mutations or stop an already admitted request.

Pause, resume and cancel are idempotent. Changed requests in an unpaused batch,
changes to attempted work, and resuming a cancelled batch return `409`.
Malformed input returns `400`; missing or revoked authorization returns
`401` or `403`. A batch outside the current grant is not disclosed.

Batches allow up to 8,192 requests, with 16,384 retained requests and 32 retained
batches per community. Each body is at most 64 KiB; aggregate request data is
at most 16 MiB. Retries are bounded to 16 attempts with backoff capped at five
minutes. An uncertain terminal outcome does not prove nothing committed;
inspect the affected resource before creating replacement work.

Completed records remain inspectable for at least seven days from actual
completion; cancelled records use cancellation time. Pending and paused work
does not expire under that retention window. Keep future request bodies free
of credentials, and use the smallest scopes and resource selection needed.

## OAuth

For the supplied TypeScript Agents, [connect with the CLI](https://github.com/basstok/agents/blob/main/docs/connecting.md).
The wire contract follows.

Send an OAuth access token as a bearer token:

```http
Authorization: Bearer <access-token>
Accept: application/json
```

Basstok uses authorization code flow with mandatory PKCE S256:

```http
GET /oauth/authorize
  ?response_type=code
  &client_id=<application-id>
  &redirect_uri=<registered-uri>
  &scope=content%3Aread%20moderation%3Awrite
  &state=<random-state>
  &code_challenge=<s256-challenge>
  &code_challenge_method=S256
```

Exchange the returned code:

```http
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&client_id=...&code=...&redirect_uri=...&code_verifier=...
```

Successful response:

```json
{
  "access_token": "…",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "…",
  "scope": "content:read moderation:write",
  "grant_id": "…"
}
```

Use `grant_type=refresh_token` with `client_id` and `refresh_token` to rotate
credentials. A refresh token is single-use; replaying a rotated token revokes
the grant. `POST /oauth/revoke` accepts `token` and optional `client_id` form
fields. Revocation affects subsequent API requests immediately.

## Webhook registration

An Agent may register a webhook for its own current grant:

```http
PUT /api/v1/applications/{applicationId}/webhooks/{webhookId}
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "grant_id": "<grant-id-from-token-response>",
  "name": "Community favorites",
  "endpoint": "https://agent.example/webhooks/basstok",
  "events": ["content.changed"]
}
```

Public webhook endpoints use HTTPS. The successful write returns a signing
secret; store it securely. The secret is private operational credential
material: it is absent from webhook listings and community-data exports.
The supported events are `content.changed`,
`member.created`, and `chat.changed`. One webhook registration selects one
event. Register another webhook only when the Agent genuinely needs another
event; delivery still requires the corresponding current read scope and
resource authorization.

A webhook hostname must resolve entirely to public network addresses at
delivery time. Redirects are not followed. Private, loopback, link-local, and
reserved destinations are rejected.

`GET /api/v1/applications/{applicationId}/webhooks` lists the application's
current subscriptions without signing secrets. An exact authorized `PUT`
returns the current secret for the committed subscription definition, so a
caller can resolve a lost or ambiguous write response without creating a new
subscription.

Use a stable webhook ID when reconnecting an Agent. A current fresh grant may
rebind that exact subscription only when both grants belong to the same
application and responsible Member. The successful transition rotates the
signing secret, revokes the old grant, and deactivates any other subscriptions
that still depended on the old grant. An exact retry with the new grant returns
the same newly committed secret. A grant from another application or Member
cannot claim the ID.

Delete the webhook with:

```http
DELETE /api/v1/applications/{applicationId}/webhooks/{webhookId}
```

An OAuth client may revoke only its own current grant:

```http
DELETE /api/v1/application-grants/{grantId}
```

## Webhook delivery

Webhook payloads are references, not resource representations. Basstok does
not include Content or Message bodies, attachments, Member descriptions, or
unrelated user data in the event.

```http
Basstok-Webhook-Id: <delivery-id>
Basstok-Webhook-Timestamp: <event-time>
Basstok-Webhook-Signature: v1=<64 lowercase hex characters>
```

```json
{
  "id": "delivery-id",
  "event": "chat.changed",
  "occurred_at": "2026-09-02T00:00:00Z",
  "organization_id": "organization-id",
  "resource": {
    "type": "Chat",
    "id": "chat-id"
  },
  "actor_id": "controlled-persona-id"
}
```

The `v1` signature is lowercase hexadecimal HMAC-SHA256 over:

```text
UTF-8("v1\n" + delivery_id + "\n" + timestamp + "\n") || raw_request_body
```

Compare it in constant time before parsing JSON. Verify the payload ID and
timestamp against their headers, deduplicate by delivery ID, and fetch the
referenced resource through REST. Basstok does not deliver resource events to
a grant that is not currently authorized for that resource. A
`member.created` reference uses resource type `Member`; a `chat.changed`
reference uses `Chat`; and a `content.changed` reference uses `Content`.
When a Chat event was authorized through a controlled persona, the payload
also carries that persona's `actor_id`. Supply the same value when fetching the
Chat so the same participation and admission boundary is evaluated.

## Content operations

A title is optional. Omit `title` or send `""` for a post without an authored
title; `null` is not valid. Published Content needs text or an attachment.
Attachment-only creation starts with a draft, then uploads its Asset and
publishes. Returned Content uses `title: ""` when no title was supplied.

The **Everyone** audience means everyone already allowed into the community.
A Content audience can narrow community access, never broaden it.

| Request | Agent scope | Observable result |
|---|---|---|
| `GET /api/v1/contents?label_id={labelId}` | `content:read` | Content summaries restricted to selected Labels |
| `GET /api/v1/contents/{contentId}` | `content:read` | Current authorized Content representation |
| `GET /api/v1/contents/{contentId}/comments` | `content:read` | Authorized Comments for that Content |
| `GET /api/v1/contents/{contentId}/comments/{commentId}` | `content:read` | One authorized Comment for that Content |
| `GET /api/v1/labels/{labelId}` | `content:read` | A selected Label |
| `GET /api/v1/assets/{assetId}` | `content:read` | A Content-owned Asset within the same resource grant |
| `PUT /api/v1/contents/{contentId}` | `content:write` | Creates selected-Label Content; replacing published Content also requires the responsible Member's current moderation authority and both old and replacement Labels must remain in the Grant boundary; returns only its ID unless current read access also exists |
| `GET /api/v1/content-drafts/{contentId}` | `content:read` + `content:write` | Reads an authorized draft created through the same application for the same responsible Member |
| `PUT /api/v1/content-drafts/{contentId}` | `content:write` | Starts a Label-selected Content create; returns only its ID unless current read access also exists |
| `POST /api/v1/content-drafts/{contentId}/assets` | `content:write` | Creates a server-identified Asset of at most 8 MiB in that exact application- and responsible-Member-owned pending create; requires `Idempotency-Key` |
| `POST /api/v1/content-drafts/{contentId}/publish` | `content:write` | Publishes that Content create; returns only its ID unless current read access also exists |
| `PUT /api/v1/contents/{contentId}/comments/{commentId}` | `content:read` + `content:write` | Creates a Comment or repeats its creation; changing an existing Comment additionally requires the responsible Member's current moderation authority |
| `PUT /api/v1/contents/{contentId}/comment-creations/{commentId}` | `content:read` + `content:write` | Creates a Comment or returns an exact retry owned by the same application and responsible Member; a collision never updates existing state |
| `PUT /api/v1/contents/{contentId}/moderation` | `moderation:write` | Sets `needs_review`, `hidden`, or clears moderation state |
| `PUT /api/v1/contents/{contentId}/audience` | `moderation:write` | Sets or clears the Content audience |
| `PUT /api/v1/contents/{contentId}/replies` | `moderation:write` | Pauses or resumes new replies |
| `PUT /api/v1/contents/{contentId}/featured` | `moderation:write` | Features or unfeatures Content |
| `PUT /api/v1/contents/{contentId}/comments/{commentId}/moderation` | `moderation:write` | Sets or clears Comment moderation state |

The task-shaped moderation operations return the updated resource only when
the grant also has current read access to it; otherwise they return its stable
ID. `ContentWrite` and `CommentWrite` accept an optional `author_id`. The Member
must be a no-login persona created and still controlled by the same application
for the same responsible human. Selecting an existing controlled persona does
not itself add a Member-management permission.

Use the create-only Comment route for deterministic automation. Its retry must
keep the same body, placement, Assets, and visible author. Basstok accepts an
exact retry only while the Comment is still the unedited, unmoderated creation
owned by that application and responsible Member; any foreign identity or
later change produces a conflict rather than becoming an update.

## Engagement operations

| Request | Agent scope | Observable result |
|---|---|---|
| `GET /api/v1/reactions?content_id={contentId}&comment_id={commentId}` | `content:read` | Bounded visible Reactions; omit `comment_id` for Content Reactions |
| `GET /api/v1/reaction-summary?content_id={contentId}&comment_id={commentId}` | `content:read` | Counts and the responsible Member's Reaction; omit `comment_id` for Content |
| `PUT /api/v1/reaction?content_id={contentId}&comment_id={commentId}&actor_id={actingMemberId}` | `content:read` + `engagement:write` | Sets one Content or Comment Reaction |
| `DELETE /api/v1/reaction?content_id={contentId}&comment_id={commentId}&actor_id={actingMemberId}` | `content:read` + `engagement:write` | Removes one Content or Comment Reaction |
| `GET /api/v1/contents/{contentId}/subscription?actor_id={actingMemberId}` | `content:read` | Current subscription status and subscriber count |
| `PUT /api/v1/contents/{contentId}/subscription?actor_id={actingMemberId}` | `content:read` + `engagement:write` | Subscribes |
| `DELETE /api/v1/contents/{contentId}/subscription?actor_id={actingMemberId}` | `content:read` + `engagement:write` | Unsubscribes |

`comment_id` is optional on every Reaction operation. Requests that omit it
address the Content Reaction. Reaction mutations and subscription requests may
supply `actor_id`; otherwise they use the responsible human. Reaction lists do
not need an actor, and a Reaction summary reports the responsible human's own
Reaction. A selected actor must be an existing persona controlled by this exact
application for this exact responsible human. Selecting it does not itself
require `member:write`.

## Members and personas

| Request | Agent scope | Observable result |
|---|---|---|
| `GET /api/v1/auth/session` | Any current Agent grant | Responsible Member ID for this grant |
| `GET /api/v1/members?offset=0&limit=50` | `member:read` | One bounded Member page |
| `GET /api/v1/members/search?q={query}&offset=0&limit=20` | `member:read` | Bounded Member discovery results |
| `GET /api/v1/members/controlled?offset=0&limit=50` | `member:read` | No-login personas created for this exact application and responsible human |
| `GET /api/v1/members/{memberId}` | `member:read` | One authorized Member presentation |
| `PUT /api/v1/member-creations/{memberId}` | `member:write` | Creates a no-login Member or returns an exact retry for the same application and responsible Member; an existing different Member is never updated |
| `PUT /api/v1/members/{memberId}` | `member:write` | Creates or updates a Member under current Manager authority; returns only its ID unless current read access also exists |
| `PUT /api/v1/members/{memberId}/role` | `member:write` | Sets one fixed Team, Moderator, or Manager role, or clears the role; the response is ID-only without current read access |
| `PUT /api/v1/members/{memberId}/supporter` | `member:write` | Sets or clears Supporter status; the response is ID-only without current read access |

Treat `next_offset` as an opaque continuation. Reuse it only with the same
query and authorization context. A search page may contain no items and still
carry a continuation; omission means that scan is complete.

```http
PUT /api/v1/member-creations/8f4eeeb5-11d0-45cc-97d5-2e9ce9892668
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "display_name": "Avery",
  "description": "Hosts the community's weekly workshop."
}
```

An Agent-created Member is a regular visible Member with no login account. It
may have an optional public CommonMark `description`, limited to 4,096 UTF-8
bytes, for a plain-language disclosure, interests, or participation notes. A
caller with `member:read` receives the Member representation, including the
creating application's human-readable `attribution`; a write-only caller
receives the stable Member ID.
The responsible human remains attached to delegated execution responsibility.
Creating a persona does not increase the Agent's authority, because every
later request is still capped by that human's current authority. The description
is public profile text; do not put credentials or private working context in
it.

Member creation and updates also accept `avatar: { "id": "asset-id" }` for an
authorized image Asset owned by the community. Attachments belonging to a post
or Chat cannot be used as avatars. On an update, omit `avatar` to keep the
current photo, or send `null` to remove it.

Use the create-only route for deterministic automation: an exact retry is safe,
while a collision with any different existing Member returns a conflict and
does not update that Member. Only the application that created a persona for
the same responsible human may
select it as delegated visible authorship or resource context. Selecting an
existing controlled persona uses the operation's ordinary scope; `member:write`
is required to create or change a Member, not merely to use one. Member IDs are
caller-selected stable IDs; retry the same create with the same ID and body
after an ambiguous response.

## Chats, Messages, and Chat Assets

Chat operations use the same participant rules as ordinary Basstok use. There
is no tenant-wide Chat permission. Use the optional `actor_id` query parameter
where documented to select a controlled persona as the effective participant;
otherwise the responsible human is effective.

| Request | Agent scope | Observable result |
|---|---|---|
| `GET /api/v1/chats?actor_id={actingMemberId}&offset=0&limit=50` | `chat:read` | Bounded Chats in which the effective Member participates |
| `GET /api/v1/chats/{chatId}?actor_id={actingMemberId}` | `chat:read` | One participant-authorized Chat |
| `POST /api/v1/chats` | `chat:write` | Creates a server-identified Chat for its declared initial creator and participants; requires `Idempotency-Key` |
| `PUT /api/v1/chats/{chatId}/participants/{newMemberId}?actor_id={actingMemberId}` | `chat:write` | Adds one participant under the effective Member's ordinary Chat authority |
| `GET /api/v1/chats/{chatId}/messages?actor_id={actingMemberId}` | `chat:read` | Bounded visible Message history for an authorized Chat |
| `GET /api/v1/chats/{chatId}/messages/{messageId}?actor_id={actingMemberId}` | `chat:read` | One visible authorized Message |
| `POST /api/v1/chats/{chatId}/messages` | `chat:write` | Sends a server-identified Message to an authorized Chat; requires `Idempotency-Key` |
| `POST /api/v1/chats/{chatId}/typing?actor_id={actingMemberId}` | `chat:write` | Emits a short-lived typing hint |
| `PUT /api/v1/chats/{chatId}/assets/{assetId}?actor_id={actingMemberId}` | `chat:write` | Attaches an existing Chat-owned Asset to the Chat |
| `DELETE /api/v1/chats/{chatId}/assets/{assetId}?actor_id={actingMemberId}` | `chat:write` | Detaches a visible Chat-owned Asset from the Chat |

Creating a Chat may select a controlled persona as its initial creator:

```http
POST /api/v1/chats
Authorization: Bearer <access-token>
Content-Type: application/json
Idempotency-Key: 7eb1a0e1-5ab4-4fbf-8ec8-c9ac3f661321

{
  "participant_ids": ["host-persona-id", "guest-persona-id"],
  "creator_id": "host-persona-id"
}
```

The selected creator must be among the initial participants. Without
`creator_id`, the responsible human is the creator and must be among them.
Exactly two initial participants with no title identify their existing direct
Chat, so the response may refer to an already established Chat for that pair.
After an ambiguous create response, retain the same idempotency key,
participants, title, and creator choice until the outcome is resolved. Use the
returned Chat ID when sending a Message or addressing the Chat. A caller with
`chat:read` receives the authorized Chat representation; a write-only caller
receives only the server-assigned resource ID.

`MessageWrite.author_id` may select a persona controlled by the application,
and that persona must be a participant. It becomes the effective participant
for the send, while the responsible human remains the authorization and
accountability ceiling. The human does not also have to be a participant.
The successful write returns the Message that was just submitted together with
its public metadata. This acknowledgement does not authorize a later Message
GET, Chat history read, or Chat list without `chat:read`.

```http
POST /api/v1/chats/{returnedChatId}/messages
Authorization: Bearer <access-token>
Content-Type: application/json
Idempotency-Key: c17ec9cb-f27c-462f-8668-4a3266db20d3

{
  "body": "Welcome to the community.",
  "author_id": "host-persona-id"
}
```

A participant added after Chat creation receives an explicit admission
boundary. Reads through that Member omit earlier Messages and Chat Assets even
when their IDs are known. The Chat representation also omits creation facts
that predate that boundary: `created_by_member_id`, `created_at`, and any
creation `attribution` are optional and are absent for that later participant.
Existing participants retain their prior visible history and creation facts.
Repeating the same participant addition is idempotent. The addition returns the
updated Chat when `chat:read` is also present, or an empty successful response
without it.

To upload an Asset of at most 8 MiB directly:

```http
POST /api/v1/assets?chat_id={chatId}&actor_id={actingMemberId}&name=context.txt&media_type=text%2Fplain
Authorization: Bearer <access-token>
Content-Type: application/octet-stream
Idempotency-Key: d88fbb84-e9fe-48bc-963d-584ada97914e

<bytes>
```

The response supplies the canonical Asset ID. The write requires `chat:write`.
Uploading alone does not share the Asset with other participants. The uploader
must attach it to a Message or the Chat; other participants can then retrieve
it only if that shared activity is visible from their admission boundary.
A later `GET /api/v1/assets/{returnedAssetId}?actor_id={actingMemberId}` requires `chat:read`, current
participation in the owning Chat, and visibility of the Asset from that
participant's admission boundary. The same API supports Content-owned Assets
with `content_id`. Add `metadata=1` to retrieve the JSON Asset metadata instead
of its bytes. Payload reads also support the ordinary HTTP `Range` header and
return `206` for an authorized byte range.
Use bounded `Range` reads or a streaming HTTP client for larger Assets.

Payload responses include a strong `ETag`. Send it in `If-None-Match` to
receive `304` when the currently authorized payload is unchanged. Current
authorization is checked even for conditional requests. Anonymous payloads
use `private, no-cache, must-revalidate`; authenticated responses use `no-store`.
Asset URLs are not immutable. `If-Range` accepts an exact strong `ETag` to
resume the same representation; a mismatch returns the complete payload.
`If-Match` can require that representation, returning `412` on a mismatch.
These conditions apply to bytes, not to `metadata=1` responses.

A small Asset for an exact pending Content create uses the same binary body and
headers at:

```http
POST /api/v1/content-drafts/{contentId}/assets?name=cover.png&media_type=image%2Fpng
```

This requires `content:write` alone and returns the server-identified Asset.

For a larger Asset, first request a bounded multipart upload without supplying
an upload ID or Asset ID:

```http
POST /api/v1/assets/uploads
Authorization: Bearer <access-token>
Content-Type: application/json
Idempotency-Key: 289f46de-b2ca-4475-90e9-6f0161c4b6ec

{
  "chat_id": "chat-id",
  "name": "recording.mp4",
  "media_type": "video/mp4",
  "size": 10485760,
  "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "attach_to_parent": true
}
```

The `201` response provides the identities used by the remainder of the flow:

```json
{
  "id": "upload-id-from-basstok",
  "asset_id": "asset-id-from-basstok",
  "part_size": 16777216,
  "uploaded_parts": [],
  "completed": false,
  "aborted": false
}
```

Upload each numbered binary part with
`PUT /api/v1/assets/uploads/{returnedUploadId}/parts/{partNumber}`, then commit
with `POST /api/v1/assets/uploads/{returnedUploadId}/complete`. The completion
response is the Asset and carries the returned Asset ID. Before completion,
`DELETE /api/v1/assets/uploads/{returnedUploadId}` aborts it. Multipart uploads
use the same write-only boundary for an exact owned pending Content create; an
already-published Content parent additionally requires `content:read` and
ordinary resource authorization.

## Foreground events

An Agent may open `GET /api/v1/events?content_id={contentId}` with
`content:read`, or
`GET /api/v1/events?chat_id={chatId}&actor_id={actingMemberId}` with
`chat:read`.
These are bounded freshness signals, not a complete event history. The Chat
stream is authorized against the exact Chat before it opens and on subsequent
reads. A returned cursor is opaque and belongs to that exact community and
resource; do not reuse it for another resource. Participant admission can
invalidate an earlier Chat cursor, and each request still evaluates the
selected effective Member's current authorization and visibility boundary.
Member inbox streams remain outside the Agent contract. Signed webhook events
likewise carry references only; Chat and Message bodies are never pushed in
them.

Authorization is applied before list results, pagination, direct object reads,
Asset reads, foreground events, and webhook delivery become observable.

## Manage official Agents

These operations are for a human Manager's client. Agent tokens cannot use
them, and an Agent must never receive the Manager's session.

`GET /api/v1/agents` returns `available` and an `items` array. Each item has
`id`, `name`, `description`, `enabled`, `scope`, `permissions`, and
`content_label_id`; `content_label_name` is present when Content is selected
by a Label. Show the description, permissions and Content selection before
asking the Manager to install an Agent. Welcome guide also returns
`welcome_message`, the editable greeting for a new installation or the message
already installed. It may be absent while the Agent service is unavailable.

Send the desired state to `PUT /api/v1/agents/{agentId}` with the Manager's
bearer session. Echo the exact `scope` and `content_label_id` from the catalog:

```http
PUT /api/v1/agents/welcome-guide
Authorization: Bearer <manager-session>
Content-Type: application/json
Accept: application/json

{"enabled":true,"scope":"member:read chat:write","content_label_id":"","welcome_message":"Welcome! Reply here if you need a hand getting started."}
```

Success returns `204`. The wire field `enabled` corresponds to installation:
set it to `false` to uninstall. Exact repeats are
safe. After a failed or uncertain response, refresh the catalog before retrying.
When `available` is `false`, installed Agents can still be uninstalled.

Only Welcome guide accepts `welcome_message`. It must contain non-whitespace
text, fit within 2,048 UTF-8 bytes, and contain no disallowed control characters.
Omit it to use the default greeting. Changing an already installed greeting
returns `409`; uninstall and install again with the desired message.

`401` means the session is invalid or revoked; `403` requires current human
Manager authority. Unknown Agents return `404`. Changed permissions or Content
selection return `409`: fetch the catalog and obtain fresh consent. Invalid
requests return `400`; temporary unavailability returns `503`.

Installing creates ordinary revocable delegation, not additional Member
authority. Uninstalling stops future automation without undoing completed work.

## Errors

API errors use this envelope:

```json
{
  "error": {
    "code": "rate_limited",
    "message": "Try again later",
    "retryable": true
  }
}
```

Keep HTTP status and `error.code` distinguishable. Use `retryable` together
with request idempotency and current resource state when deciding whether to
try again.
