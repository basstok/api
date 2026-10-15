# Contributing

Keep changes focused on the public Basstok REST API. Update the
[reference](../reference.md) and [OpenAPI contract](../openapi.json) together
when a published operation changes. Do not document unimplemented endpoints.

From the repository root, with Node.js 24 or newer:

```sh
node scripts/check.mjs
python3 -m unittest discover -s examples -p 'test_*.py' -v
```

No installation is needed. The check validates OpenAPI references, operation
identities, security declarations, and documentation links. It does not test a
running Basstok service. The Python 3.10+ example tests use only the standard
library and fake API responses; no credentials or live service are needed.

Do not include credentials or private community data in examples or issues.
Report sensitive issues privately to [Basstok](mailto:mail@basstok.com).
