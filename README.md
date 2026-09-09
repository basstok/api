# Basstok REST API

The public API for [Basstok](https://basstok.com/): Content and discussion,
Members, Messages, files, Calls, and community management.

One ordinary HTTPS/JSON interface serves native clients and external Agents.
Each request uses the permissions of the Member or delegated grant making it.

**[Read the reference](reference.md)** · **[OpenAPI contract](openapi.json)** · **[Build an Agent](https://github.com/basstok/agents)**

## Connect to a community

Requests go to the community's own hostname. There is no separate central API host.

```ts
const response = await fetch("https://community.example/api/v1/context");
if (!response.ok) throw new Error(`Basstok returned ${response.status}`);
const community = await response.json();
```

This public request identifies the community. Reading or changing protected
resources requires the appropriate authentication and resource access.

## What you can build

- **Community clients:** publish Content, add nested Comments, search, react,
  and follow discussions.
- **Messaging experiences:** work with participant-authorized Chats, Messages,
  and attachments.
- **Native experiences:** Member sign-in, notifications, push registration,
  Connections, and audio/video Call signaling and recording consent.
- **Management tools:** manage Members, moderation, public Website publication,
  official Agent installation, [custom domains](reference.md#connect-a-domain),
  customer storage connections, and community email.
- **Agents and importers:** use delegated OAuth grants for automation or the
  separately authorized historical-import contract.
- **Scheduled publishing:** submit future API requests once; inspect, pause,
  correct or cancel them without keeping an Agent online.

[OpenAPI](openapi.json) specifies the supported requests, schemas, and
authentication for each operation. A community's `/openapi.json` describes its
installed release; [view the contract served by basstok.com](https://basstok.com/openapi.json).
Check that installed contract for operation availability before connecting.

## Access stays explicit

Signed-in clients use a Member session. Agents use OAuth with scoped,
revocable delegation from one responsible Member. Scopes are a limit, not a
substitute for resource access. Private Chats require participation; newly
added participants cannot read earlier history.

Webhooks carry signed references. Fetch the referenced resource through the
API using current authorization. Revocation stops subsequent access.

The [reference](reference.md) covers authentication, permissions, safe retries,
resource operations, and events. It also distinguishes Member-only operations
from those available through Agent grants.

## Around the API

[Basstok Agents](https://github.com/basstok/agents) has ready-to-run programs
and their results. [Basstok storage](https://github.com/basstok/storage)
explains customer custody and portability.

[Contributing and checks](.github/CONTRIBUTING.md) · [MIT](LICENSE)
· [Contact Basstok](mailto:mail@basstok.com)
