import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const spec = JSON.parse(readFileSync(resolve(root, "openapi.json"), "utf8"));
assert.match(spec.openapi, /^3\.1\.\d+$/);
const methods = new Set(["get", "put", "post", "delete", "patch", "head", "options"]);
const operationIds = new Set();
const operations = [];

function reference(pointer) {
  assert.ok(pointer.startsWith("#/"), `Non-local reference: ${pointer}`);
  return pointer.slice(2).split("/").reduce((value, part) => {
    const key = part.replaceAll("~1", "/").replaceAll("~0", "~");
    assert.ok(value && Object.hasOwn(value, key), `Missing reference: ${pointer}`);
    return value[key];
  }, spec);
}

function walk(value) {
  if (!value || typeof value !== "object") return;
  if (typeof value.$ref === "string") reference(value.$ref);
  for (const child of Object.values(value)) walk(child);
}
walk(spec);

for (const [path, method] of [
  ["/api/v1/organization/storage", "get"],
  ["/api/v1/organization/storage/verify", "post"],
]) {
  assert.deepEqual(Object.keys(spec.paths[path]), [method]);
  assert.deepEqual(spec.paths[path][method].security, [{ memberBearer: [] }]);
}
assert.deepEqual(Object.keys(spec.components.schemas.OrganizationStorage.properties), ["custody", "target"]);
assert.equal(spec.components.schemas.CustomerStorageCheck.properties.credentials.writeOnly, true);

for (const [path, item] of Object.entries(spec.paths)) {
  assert.ok(path.startsWith("/"));
  for (const [method, operation] of Object.entries(item)) {
    if (!methods.has(method)) continue;
    assert.ok(operation.operationId, `${method} ${path} needs an operationId`);
    assert.ok(!operationIds.has(operation.operationId), `Duplicate operationId: ${operation.operationId}`);
    operationIds.add(operation.operationId);
    operations.push([method.toUpperCase(), path]);
    assert.ok(Object.keys(operation.responses).length > 0);
    for (const requirement of operation.security ?? spec.security ?? []) {
      for (const [name, scopes] of Object.entries(requirement)) {
        const scheme = spec.components.securitySchemes[name];
        assert.ok(scheme, `Unknown security scheme: ${name}`);
        const allowed = Object.values(scheme.flows ?? {}).flatMap(flow => Object.keys(flow.scopes));
        for (const scope of scopes) assert.ok(allowed.includes(scope), `Unknown scope: ${scope}`);
      }
    }
    const parameters = [...(item.parameters ?? []), ...(operation.parameters ?? [])]
      .map(p => p.$ref ? reference(p.$ref) : p);
    for (const [, name] of path.matchAll(/\{([^}]+)\}/g)) {
      assert.ok(parameters.some(p => p.in === "path" && p.name === name && p.required),
        `Missing path parameter: ${method} ${path} ${name}`);
    }
  }
}

for (const file of ["README.md", "reference.md"]) {
  const text = readFileSync(resolve(root, file), "utf8");
  for (const [, target] of text.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
    if (/^(https?:|mailto:)/.test(target)) continue;
    const [path, anchor] = target.split("#");
    const destination = path ? resolve(root, dirname(file), path) : resolve(root, file);
    assert.ok(existsSync(destination), `${file}: missing link ${target}`);
    if (anchor && destination.endsWith(".md")) {
      const headings = [...readFileSync(destination, "utf8").matchAll(/^#+ (.+)$/gm)]
        .map(([, heading]) => heading.toLowerCase().replace(/[^\p{L}\p{N}_\- ]/gu, "").replaceAll(" ", "-"));
      assert.ok(headings.includes(anchor), `${file}: missing anchor ${target}`);
    }
  }
  for (const [, method, path] of text.matchAll(/\b(GET|PUT|POST|DELETE|PATCH) (\/[^\s?`]+)/g)) {
    assert.ok(operations.some(([candidateMethod, template]) => {
      const parts = template.split(/(\{[^}]+\})/).map(part => part.startsWith("{")
        ? "[^/]+" : part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
      return candidateMethod === method && new RegExp(`^${parts.join("")}$`).test(path);
    }), `${file}: undocumented operation ${method} ${path}`);
  }
}

console.log(`Checked ${Object.keys(spec.paths).length} paths, ${operations.length} operations, local references, permissions, and documentation links.`);
