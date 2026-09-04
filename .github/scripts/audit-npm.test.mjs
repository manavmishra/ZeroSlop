import assert from "node:assert/strict";
import test from "node:test";

import { classifyAuditFailure } from "./audit-npm.mjs";

test("retries only transport and retired-endpoint failures", () => {
  for (const message of [
    "503 Service Unavailable; audit endpoint returned an error",
    "request timed out",
    "ECONNRESET",
    "This endpoint is being retired. Use the bulk advisory endpoint instead.\n400 Bad Request\nInvalid package tree",
  ]) {
    assert.equal(classifyAuditFailure(message), "retry", message);
  }
});

test("fails immediately when npm returns an audit report with findings", () => {
  const report = JSON.stringify({
    auditReportVersion: 2,
    vulnerabilities: { dependency: { severity: "high" } },
  });
  assert.equal(classifyAuditFailure(report), "findings");
});

test("does not disguise local package errors as registry failures", () => {
  assert.equal(classifyAuditFailure("npm error invalid package lock"), "fatal");
});
