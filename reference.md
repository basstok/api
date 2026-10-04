# Basstok API guide

[OpenAPI](openapi.json) is the complete reference for paths, request bodies,
responses, bounds and authentication. Each deployed service also publishes its
contract at `/openapi.json`. This guide avoids duplicating an endpoint catalog
that could drift from the service.

## Accounts and sessions

A personal Account or community is an Organization. Use its HTTPS origin.
Read `GET /api/v1/context` to identify it. Member identities, permissions and
data are Organization-scoped; there is no global token granting access everywhere.

Ordinary onboarding creates a usable session without credential enrollment.
Unsaved access depends on that browser/device session. Account security can
later add a passkey or verified email sign-in for the same Member. Recovery
and founder Admin activation are separate.

Signed-in API clients use the `memberBearer` security scheme. Web clients also
observe the contract's same-origin, cookie and browser-presence requirements.
`GET /api/v1/auth/session` reads the session;
`DELETE /api/v1/auth/session` revokes it.
Keep sessions, authorization codes and provider credentials out of public
examples, issue reports and logs. Do not replay an uncertain login operation
or create a replacement Member to regain existing access.

## Authorization

User-facing role wording is **Admin**; the contract's authority value remains
`manager`. Use exact enum values rather than translated labels.
Content audience and moderation apply to Comments too. Ordinary Labels organize
discovery, not permissions. Chats require participation; joining later does not
expose earlier history. Attachments inherit their owner's access rules.

Initial founders may preview administration but cannot commit Admin changes
before the separate recovery-email activation. Saving a login method does not
grant Admin authority.

An **App** uses explicit OAuth delegation from a currently authorized Member.
Scopes cap that Member's authority, and selected resources still matter.
Consult each operation's `security` declaration: Member-only operations do not
become available to an App merely because it has a broadly named scope.

Provider consent for DNS or email is separate from Basstok login.
A provider callback does not grant Member or Admin authority. Reread connection
status and follow its explicit next step rather than assuming a redirect means
the capability is ready.

## Communication

Chats and Messages provide shared authorized history. External email addresses
and phone numbers are sender information, not authenticated Membership.
Receiving a message does not grant its sender access to Chat history.

SIP MESSAGE and carrier SMS are distinct capabilities. Replies require an
explicit recipient and actual sending support. Compatible SIP accounts provide
native telephone calling; browser telephone calling is not offered. Fax uses
document Assets and requires compatible provider support.

Use reported connection and operation states. A saved credential or phone number
does not prove working calls, background ringing or fax delivery. Customer
provider onboarding, billing and consent remain explicit.

Foreground events, in-app notifications and native push have different delivery
purposes. Notification destinations must pass current access checks.
Authenticate and deduplicate signed webhooks, then reread their referenced
resource through the authorized API. Optional notification email remains
separate from required authentication, recovery and security delivery.

## Retries and limits

Follow each operation's documented status codes, limits and retry semantics.
Do not blindly retry purchases, provider code exchanges or external sends after
losing a response. Reread operation status where supported: a timeout does not
prove that no action occurred.

Keep IDs opaque. Pagination is not a resource count or authorization grant.
Errors must not cause private data to be republished with broader access.

## Import existing data

The [small import example](https://github.com/basstok/import) uses the public
import API. Import requires a current human Admin session, not an App token or
direct bucket access. Historical Members and authorship do not become login
credentials or Admin grants.

Preserve original source evidence, deterministic identities, ordered batches
and completed-receipt verification. A received batch is not a completed import.
After failure, follow the explicit whole-run restart behavior, not automatic
retries or invented partial-success recovery. Test privately before cutover.

## Data and support

[Storage documentation](https://github.com/basstok/storage) explains Account
custody, customer-owned buckets and exports. Use authorized Basstok operations
to change data. Direct bucket edits are not an API or repair mechanism.

English copy is canonical while product wording stabilizes; existing translations
may fall back to English. Never translate IDs, scopes or contract values.

[Contributing](.github/CONTRIBUTING.md) describes offline contract checks.
Report sensitive issues privately to [Basstok](mailto:mail@basstok.com).
