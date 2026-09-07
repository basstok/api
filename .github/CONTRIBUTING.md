# Contributing

Keep changes focused on the public Basstok REST API. Update the
[reference](../reference.md) and [OpenAPI contract](../openapi.json) together
when a published operation changes. Do not document unimplemented endpoints.

From the repository root, with Node.js 24 or newer:

```sh
node scripts/check.mjs
```

No installation is needed. The check validates OpenAPI references, operation
identities, security declarations, and documentation links. It does not test a
running Basstok service.

Do not include credentials or private community data in examples or issues.
Report sensitive issues privately to [Basstok](mailto:mail@basstok.com).
