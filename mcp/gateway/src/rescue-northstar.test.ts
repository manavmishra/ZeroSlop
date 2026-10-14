import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { localRescue, sourceClaimRisk } from "./pipeline";

const rescueScript = fileURLToPath(new URL("../../../scripts/rescue.py", import.meta.url));
const source = "We’re thrilled to announce a game-changing update to Project Northstar. " +
  "Starting October 20, teams can export their weekly report as a CSV file. " +
  "It is important to note that Maya owns the rollout, and the beta is limited to 25 teams. " +
  "This seamless experience empowers teams to unlock actionable insights.";
const expected = "We’re thrilled to announce an update to Project Northstar. " +
  "Starting October 20, teams can export their weekly report as a CSV file. " +
  "Maya owns the rollout, and the beta is limited to 25 teams. " +
  "This seamless experience empowers teams to unlock actionable insights.";

function parity(input: string, output: string) {
  assert.equal(localRescue(input), output);
  assert.equal(execFileSync("python3", [rescueScript, "-"], {
    input, encoding: "utf8",
  }).trimEnd(), output);
  assert.equal(localRescue(output), output);
}

test("Northstar fallback removes hype without paraphrasing emotion or benefit", () => {
  parity(source, expected);
  assert.equal(sourceClaimRisk(source, expected), false);
  assert.equal(sourceClaimRisk(source, expected.replace("teams can export", "teams cannot export")), true);
  assert.equal(sourceClaimRisk(source, expected.replace("Starting October 20", "Starting October 21")), true);
  assert.equal(sourceClaimRisk(source, expected.replace("empowers teams", "does not empower teams")), true);
});

test("announcements and unspecified benefit claims keep their literal meaning", () => {
  for (const verb of ["’re", "'re", " are"]) for (const noun of ["an update to iOS", "a release for eBay and NASA"]) {
    parity(`We${verb} thrilled to announce ${noun}.`, `We${verb} thrilled to announce ${noun}.`);
  }
  for (const agent of ["teams", "users", "people"]) {
    parity(`This seamless experience empowers ${agent} to unlock actionable insights.`,
      `This seamless experience empowers ${agent} to unlock actionable insights.`);
  }
});

test("Northstar fallback preserves quotation, code, Markdown and URL bytes", () => {
  for (const protectedSpan of [
    `"${source}"`, `“${source}”`, `‘${source}’`, `'${source}'`,
    "'We're thrilled to announce a game-changing update to Project Northstar.'",
    `\x60${source}\x60`, `\x60\x60\x60text\n${source}\n\x60\x60\x60`, `> ${source}`,
    "[We’re thrilled to announce](https://example.test/game-changing-update)",
    "https://example.test/seamless-experience?owner=Maya&teams=25",
  ]) {
    parity(protectedSpan, protectedSpan);
    parity(`${source}\n\n${protectedSpan}`, `${expected}\n\n${protectedSpan}`);
  }
});

test("Northstar fallback leaves qualifiers, negative claims and already-clear text alone", () => {
  const claim = "Maya may not approve the rollout before October 20. " +
    "iOS and eBay cannot export CSV; NASA will not join the 25-team beta.";
  parity(`${source} ${claim}`, `${expected} ${claim}`);
  assert.equal(sourceClaimRisk(`${source} ${claim}`, `${expected} ${claim}`), false);
  for (const input of [
    "We are not thrilled to announce an update to iOS.",
    "We were thrilled to announce an update to iOS.",
    "Maya said we are thrilled to announce an update to iOS.",
    "We are thrilled to announce that the beta may not launch.",
    "This experience does not empower teams to find insights.",
    "This seamless experience may empower teams to unlock actionable insights.",
    "This seamless experience empowers teams to unlock actionable insights only after approval.",
    "This Seamless Experience empowers teams to unlock actionable insights.",
    "The report shows 25 teams can export CSV on October 20.",
  ]) parity(input, input);
});

test("complete multiline quotations preserve their content and internal apostrophes", () => {
  for (const [opening, closing] of [["“", "”"], ["‘", "’"], ['"', '"'], ["'", "'"]]) {
    for (const verb of ["’re", "'re"]) {
      const quoted = `${opening}Maya said:\n\nWe${verb} thrilled to announce an update to Project Northstar.\n` +
        "This seamless experience empowers teams to unlock actionable insights.\n" + closing;
      parity(quoted, quoted);
      parity(`${source}\n\n${quoted}`, `${expected}\n\n${quoted}`);
    }
  }
});
