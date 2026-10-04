# Basstok REST API

[Basstok](https://basstok.com/) brings messaging, calls, email and documents
together. Compatible customer-owned phone services can add telephone calls,
texts and fax. Communities are optional, not a prerequisite for using Basstok.

This is the public HTTPS/JSON contract for clients and integrations. It describes
implemented operations, not a guarantee that every provider or device is ready.
Telephone audio uses the native apps, not the browser.

**[API guide](reference.md)** · **[OpenAPI](openapi.json)** ·
**[Deployed contract](https://basstok.com/openapi.json)**

## Start with the right Account

Each personal Account or community is an Organization with its own data and
permissions. Use its HTTPS hostname for requests. Joining a community does not
create a separate personal Account or grant access to another one.

```javascript
const response = await fetch("https://account.example/api/v1/context");
if (!response.ok) throw new Error(`Basstok returned ${response.status}`);
const context = await response.json();
```

Starting an Account does not require a password, passkey or email. Access first
depends on that browser/device session; save a passkey or verified email login
later in Account security. Admin activation has its own recovery-email check.

## Build around communication

- Participant-authorized Chats, Messages, attachments and audio/video Calls.
- Incoming email and connected mailboxes, with external senders distinct from Members.
- Phone connections, explicit text recipients and document-based fax operations,
  where the connected service supports them.
- Content, Comments, Labels, Member profiles, discovery and notifications.
- Admin-authorized domains, storage, imports and scoped application access.

An App grant is revocable delegation from a Member, not a permission bypass.
Private Chats retain their participant and history boundaries. Do not give an
integration a human session when scoped OAuth is appropriate.

The contract is synchronized with verified Web/backend deployments. Check the
target Organization's `/openapi.json` before using an operation. API publication
does not establish live carrier interoperability or physical-device behavior.

[Import existing data](https://github.com/basstok/import) ·
[Data and storage](https://github.com/basstok/storage) ·
[Contributing](.github/CONTRIBUTING.md) · [MIT](LICENSE) ·
[Contact](mailto:mail@basstok.com)
