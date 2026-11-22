// Directly exercise production functions offline; no hosted model call.
import { readFileSync } from "node:fs";
import { localRescue, sourceClaimRisk } from "../../mcp/gateway/src/pipeline";

const drafts = JSON.parse(readFileSync(new URL("./drafts.json", import.meta.url), "utf8"));
const pairs = JSON.parse(readFileSync(new URL("./pairs.json", import.meta.url), "utf8"));
console.log(JSON.stringify({
  drafts: drafts.map((row: { id: string; source: string }) => ({ id: row.id, edited: localRescue(row.source) })),
  pairs: pairs.map((row: { id: string; source: string; rewrite: string; expected_review: boolean }) => ({
    id: row.id, expected_review: row.expected_review, review: sourceClaimRisk(row.source, row.rewrite),
  })),
}, null, 2));
