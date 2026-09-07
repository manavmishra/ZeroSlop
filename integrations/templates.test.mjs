import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const collection = JSON.parse(await readFile(new URL("./postman/zero-slop.postman_collection.json", import.meta.url), "utf8"));
const workflow = JSON.parse(await readFile(new URL("./n8n/zero-slop-review.workflow.json", import.meta.url), "utf8"));
const statuses = ["rewritten", "rewritten_with_warnings", "already_clear", "unchanged_no_better_version", "unchanged_verification_failed", "unchanged_service_unavailable"];

function fixture(status = "rewritten") {
  const clear = status === "already_clear";
  return {
    text: "Maya owns the pricing review.", status,
    before: { score: clear ? 10 : 60 }, after: { score: 10 }, scoreChange: clear ? 0 : -50,
    factsPreserved: true, passedFinalChecks: status === "rewritten",
    independentModelChecks: 0, modelRequests: status === "already_clear" ? 0 : 1,
    rolesCompleted: 8, finishingRounds: 0, scorerVersion: "2.10.0",
    durationMs: 1000, note: "Synthetic test result.",
  };
}

function expectations(value) {
  const chain = {};
  chain.to = chain; chain.be = chain; chain.have = chain;
  chain.property = (key) => { assert(value !== null && typeof value === "object" && key in value); return chain; };
  chain.eql = (other) => { assert.deepEqual(value, other); return chain; };
  chain.a = chain.an = (type) => { assert.equal(typeof value, type); return chain; };
  chain.oneOf = (values) => { assert(values.includes(value)); return chain; };
  chain.within = (min, max) => { assert(typeof value === "number" && value >= min && value <= max); return chain; };
  chain.match = (regex) => { assert(regex.test(value)); return chain; };
  chain.include = (substring) => { assert(value.includes(substring)); return chain; };
  return chain;
}

function runPostman(item, code, payload, contentType = "application/json") {
  const variables = new Map();
  const failures = [];
  const pm = {
    test: (name, fn) => { try { fn(); } catch { failures.push(name); } },
    expect: expectations,
    variables: { set: (key, value) => variables.set(key, value) },
    response: { code, json: () => payload, headers: { get: () => contentType }, to: { have: { status: (expected) => assert.equal(code, expected) } } },
  };
  for (const event of item.event || []) {
    if (event.listen === "test") vm.runInNewContext(event.script.exec.join("\n"), { pm }, { timeout: 100 });
  }
  return { variables, failures };
}

function expression(value, $json) {
  assert(value.startsWith("={{") && value.endsWith("}}"));
  return vm.runInNewContext(value.slice(3, -2).trim(), { $json }, { timeout: 100 });
}

test("Postman requests have no credentials, no redirects, and valid synthetic JSON", () => {
  assert.equal(collection.auth.type, "noauth");
  assert.equal(collection.variable[0].value, "https://mcp.zero-slop.ai");
  for (const item of collection.item) {
    assert.equal(item.protocolProfileBehavior.followRedirects, false);
    assert(item.request.url.startsWith("{{baseUrl}}/"));
    assert(!item.request.header.some((header) => /authorization|cookie/i.test(header.key)));
    if (item.request.body) assert.doesNotThrow(() => JSON.parse(item.request.body.raw));
  }
});

test("Postman accepts six valid outcomes without falsely approving warnings", () => {
  for (const status of statuses) {
    const result = runPostman(collection.item[1], 200, fixture(status));
    assert.deepEqual(result.failures, []);
    assert.equal(result.variables.get("reviewRequired"), !["rewritten", "already_clear"].includes(status));
    assert.equal(result.variables.size, 1);
  }
  const malformed = fixture();
  malformed.passedFinalChecks = "true";
  assert(runPostman(collection.item[1], 200, malformed).failures.length);
  for (const changes of [{ modelRequests: 1 }, { scoreChange: -1 }, { before: { score: 60 } }, { before: {}, after: {} }]) {
    assert.equal(runPostman(collection.item[1], 200, { ...fixture("already_clear"), ...changes }).variables.get("reviewRequired"), true);
  }
});

test("Postman schema and structured-error examples run against fixture responses", () => {
  assert.deepEqual(runPostman(collection.item[0], 200, {
    openapi: "3.1.2", paths: { "/v1/deslop": { post: { operationId: "deslop" } } }, components: { schemas: { DeslopResult: {} } },
  }).failures, []);
  assert.deepEqual(runPostman(collection.item[2], 400, {
    type: "about:blank", title: "Invalid input", status: 400, detail: "Check your draft.", code: "invalid_input", requestId: "fixture-id",
  }, "application/problem+json").failures, []);
  assert(runPostman(collection.item[1], 429, {}).failures.length);
});

test("n8n workflow is manual, inactive, credential-free, and does not persist execution history", () => {
  assert.equal(workflow.active, false);
  assert.deepEqual(workflow.pinData, {});
  assert.equal(workflow.settings.saveManualExecutions, false);
  assert.equal(workflow.settings.saveExecutionProgress, false);
  assert.equal(workflow.settings.saveDataErrorExecution, "none");
  assert.equal(workflow.settings.saveDataSuccessExecution, "none");
  assert.equal(workflow.settings.callerPolicy, "none");
  assert.equal(workflow.nodes.filter((node) => node.type === "n8n-nodes-base.manualTrigger").length, 1);
  assert(!workflow.nodes.some((node) => node.credentials || /webhook|schedule|slack|email|gmail/i.test(node.type)));
  const names = new Set(workflow.nodes.map((node) => node.name));
  for (const [source, connection] of Object.entries(workflow.connections)) {
    assert(names.has(source));
    for (const output of connection.main) for (const link of output) assert(names.has(link.node));
  }
});

test("n8n HTTP body matches REST, with no retries or redirects", () => {
  const node = workflow.nodes.find((node) => node.type === "n8n-nodes-base.httpRequest");
  assert.equal(node.parameters.url, "https://mcp.zero-slop.ai/v1/deslop");
  assert.equal(node.parameters.method, "POST");
  assert.equal(node.parameters.authentication, "none");
  assert.equal(node.parameters.options.timeout, 75_000);
  assert.equal(node.parameters.options.redirect.redirect.followRedirects, false);
  assert.equal(node.retryOnFail, false);
  assert.equal(node.onError, "stopWorkflow");
  const input = { text: "A quote: \"hello\".\nNext line.", genre: "general", audience: "Readers" };
  assert.deepEqual(JSON.parse(expression(node.parameters.jsonBody, input)), input);
});

test("n8n approval gate covers every status and rejects loose booleans or unknown outcomes", () => {
  const node = workflow.nodes.find((node) => node.name === "Checks passed");
  const approval = node.parameters.conditions.conditions[0].leftValue;
  for (const status of statuses) {
    assert.equal(expression(approval, fixture(status)), ["already_clear", "rewritten"].includes(status));
    assert.equal(expression(approval, { ...fixture(status), factsPreserved: false }), false);
  }
  assert.equal(expression(approval, { ...fixture(), factsPreserved: "true" }), false);
  assert.equal(expression(approval, { ...fixture(), passedFinalChecks: "true" }), false);
  assert.equal(expression(approval, { ...fixture(), status: "future_status" }), false);
  for (const changes of [{ modelRequests: 1 }, { scoreChange: -1 }, { before: { score: 60 } }, { before: {}, after: {} }]) {
    assert.equal(expression(approval, { ...fixture("already_clear"), ...changes }), false);
  }
  const outputs = workflow.connections["Checks passed"].main;
  assert.equal(outputs[0][0].node, "Ready for human review");
  assert.equal(outputs[1][0].node, "Review warnings or keep original");
  assert.equal(workflow.connections["Ready for human review"], undefined);
  assert.equal(workflow.connections["Review warnings or keep original"], undefined);
});

test("n8n Code nodes return synthetic input and review-only output without network calls", () => {
  for (const node of workflow.nodes.filter((node) => node.type === "n8n-nodes-base.code")) {
    const output = vm.runInNewContext(`(function () { ${node.parameters.jsCode} })()`, { $input: { all: () => [{ json: fixture() }] } }, { timeout: 100 });
    assert.equal(output.length, 1);
    if (node.name === "Synthetic draft") assert.equal(output[0].json.genre, "professional");
    else assert.equal(output[0].json.result.text, fixture().text);
  }
});
