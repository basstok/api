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

for (const name of ["HistoricalRoute", "PublicRoute"]) {
  assert.ok(spec.components.schemas[name].required.includes("preferred"));
  assert.equal(spec.components.schemas[name].properties.preferred.type, "boolean");
}
assert.equal(spec.components.schemas.PublicRouteBody.properties.preferred.default, false);
assert.equal(spec.components.schemas.PublicRouteBody.properties.preferred.type, "boolean");

assert.deepEqual(spec.components.schemas.PrimaryColor.enum,
  ["rose", "orange", "amber", "lime", "emerald", "cyan", "blue", "violet", "fuchsia"]);
assert.deepEqual(spec.paths["/api/v1/organization/appearance"].put.security, [{memberBearer: []}]);
assert.equal(spec.paths["/api/v1/organization/homepage"], undefined);
assert.equal(spec.paths["/api/v1/site"], undefined);
assert.ok(!Object.keys(spec.components.schemas).some(name => name === "Homepage" || name.startsWith("Website")));
assert.deepEqual(spec.paths["/api/v1/organization/pin"].put.security, [{memberBearer: []}]);
assert.deepEqual(spec.paths["/api/v1/organization/pin"].get.security, [{memberBearer: []}, {}]);
assert.deepEqual(spec.components.schemas.HomePin.required, ["content_id"]);
assert.deepEqual(spec.components.schemas.HomePin.properties.content_id.type, ["string", "null"]);
assert.equal(spec.components.schemas.HomePin.additionalProperties, false);
const notifications = spec.paths["/api/v1/organization/notifications"].put;
assert.deepEqual(notifications.security, [{memberBearer: []}]);
assert.deepEqual(notifications.requestBody.content["application/json"].schema.required, ["paused"]);
assert.equal(notifications.requestBody.content["application/json"].schema.properties.paused.type, "boolean");
assert.ok(spec.components.schemas.Organization.required.includes("notifications_paused"));
assert.match(notifications.description, /does not replay/);
assert.match(notifications.description, /never community SMTP/);
for (const [path, allowedMethods] of [
  ["/api/v1/import-preparation", ["get"]],
  ["/api/v1/import-preparation/{preparationId}/inputs", ["put"]],
  ["/api/v1/import-preparation/{preparationId}/inputs/{inputId}/{part}", ["put", "get"]],
  ["/api/v1/import-preparation/{preparationId}/start", ["post"]],
  ["/api/v1/import-preparation/{preparationId}/edit", ["post"]],
]) {
  const item = spec.paths[path];
  assert.deepEqual(Object.keys(item).filter(key => methods.has(key)), allowedMethods);
  for (const method of allowedMethods)
    assert.deepEqual(item[method].security, [{memberBearer: []}]);
}
assert.equal(spec.components.schemas.PreparedImport.properties.inputs.maxItems, 3);
assert.equal(spec.components.schemas.ImportInputWrite.properties.size.maximum, 8 * 1024 ** 3);
assert.equal(spec.components.schemas.ImportInput.properties.part_sha256.maxItems, 512);
assert.equal(spec.paths["/api/v1/import-preparation/{preparationId}/start"].post.requestBody, undefined);
assert.equal(spec.paths["/api/v1/import-preparation/{preparationId}/edit"].post.requestBody, undefined);
const memberQuery = spec.paths["/api/v1/members"].get.parameters.find(p => p.name === "q");
assert.equal(memberQuery.in, "query");
assert.equal(memberQuery.schema.maxLength, 256);

for (const [path, allowedMethods] of [
  ["/api/v1/organization/domains", ["get", "post"]],
  ["/api/v1/organization/domains/{domainId}/verify", ["post"]],
  ["/api/v1/organization/domains/{domainId}", ["delete"]],
]) {
  const item = spec.paths[path];
  assert.deepEqual(Object.keys(item).filter(key => methods.has(key)), allowedMethods);
  for (const method of allowedMethods) {
    assert.deepEqual(item[method].security, [{ memberBearer: [] }]);
    assert.equal(item[method].responses["200"].content["application/json"].schema.$ref,
      "#/components/schemas/OrganizationDomains");
  }
}
assert.deepEqual(spec.components.schemas.CustomDomain.properties.state.enum, ["pending", "active"]);
assert.equal(spec.components.schemas.OrganizationDomains.properties.domains.maxItems, 4);
assert.equal(spec.paths["/api/v1/organization/domains/{domainId}/verify"].post.requestBody, undefined);
assert.equal(spec.paths["/api/v1/organization/domains/{domainId}"].delete.requestBody, undefined);

for (const [path, method] of [
  ["/api/v1/organization/storage", "get"],
  ["/api/v1/organization/storage/verify", "post"],
  ["/api/v1/organization/storage/activate", "post"],
  ["/api/v1/organization/storage/resume", "post"],
]) {
  assert.deepEqual(Object.keys(spec.paths[path]), [method]);
  assert.deepEqual(spec.paths[path][method].security, [{ memberBearer: [] }]);
}
assert.deepEqual(Object.keys(spec.components.schemas.OrganizationStorage.properties), ["custody", "target", "transfer"]);
assert.deepEqual(spec.components.schemas.OrganizationStorage.properties.custody.enum,
  ["managed", "transferring", "customer_owned"]);
assert.equal(spec.paths["/api/v1/organization/storage/resume"].post.requestBody, undefined);
assert.equal(spec.components.schemas.CustomerStorageCheck.properties.credentials.writeOnly, true);

for (const [path, allowedMethods] of [
  ["/api/v1/organization/email", ["get", "put"]],
  ["/api/v1/organization/email/verify", ["post"]],
]) {
  assert.deepEqual(Object.keys(spec.paths[path]), allowedMethods);
  for (const method of allowedMethods)
    assert.deepEqual(spec.paths[path][method].security, [{ memberBearer: [] }]);
}
assert.equal(spec.components.schemas.CommunitySmtpInput.properties.credentials.writeOnly, true);
assert.deepEqual(Object.keys(spec.components.schemas.OrganizationEmail.properties), ["smtp"]);

for (const [path, allowedMethods] of [
  ["/api/v1/schedules/{scheduleId}", ["put", "get", "delete"]],
  ["/api/v1/schedules/{scheduleId}/pause", ["post"]],
  ["/api/v1/schedules/{scheduleId}/resume", ["post"]],
]) {
  const item = spec.paths[path];
  assert.deepEqual(Object.keys(item).filter(key => methods.has(key)), allowedMethods);
  for (const method of allowedMethods) assert.deepEqual(item[method].security, [{ oauth: [] }]);
}
assert.equal(spec.components.schemas.ScheduledRequest.additionalProperties, false);
assert.deepEqual(spec.components.schemas.ScheduledRequest.required, ["execute_at", "request"]);
assert.deepEqual(spec.components.schemas.ScheduledRequest.properties.request.properties.method.enum, ["PUT", "POST"]);
assert.equal(spec.components.schemas.ScheduledBatch.properties.requests.maxItems, 8192);
assert.equal(spec.components.schemas.ScheduledBatch.properties.attempts.maximum, 16);
assert.equal(spec.components.schemas.ScheduledBatch.properties.paused_at.format, "date-time");
assert.match(spec.paths["/api/v1/schedules/{scheduleId}"].put.description,
  /no application-defined future scheduling horizon/);

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

for (const file of ["README.md", "reference.md", ".github/CONTRIBUTING.md"]) {
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
