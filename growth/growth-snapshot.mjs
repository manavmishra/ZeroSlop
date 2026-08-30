#!/usr/bin/env node
// Daily growth snapshot.
//
// GitHub's traffic API retains only 14 days, so referrer and clone history is
// destroyed unless it is captured every day. This writes one JSON line per run.
//
// The valuable call is /stargazers with the star+json media type: it returns a
// starred_at timestamp per star, which turns the star count into an event
// stream and is what makes campaign attribution windows possible at all.
//
// Env: GITHUB_TOKEN (repo read), REPO (owner/name), OUT (default growth-data.jsonl)

const repo = process.env.REPO || "manavmishra/ZeroSlop";
const token = process.env.GITHUB_TOKEN;
const out = process.env.OUT || "growth-data.jsonl";

if (!token) {
  console.error("GITHUB_TOKEN is required");
  process.exit(1);
}

const base = "https://api.github.com";
const headers = {
  Accept: "application/vnd.github+json",
  Authorization: `Bearer ${token}`,
  "X-GitHub-Api-Version": "2022-11-28",
  "User-Agent": "zero-slop growth snapshot",
};

async function get(path, accept) {
  const res = await fetch(`${base}${path}`, {
    headers: accept ? { ...headers, Accept: accept } : headers,
  });
  if (!res.ok) {
    console.error(`${path} -> ${res.status}`);
    return null;
  }
  return res.json();
}

// Stargazers are paginated at 100. Walk every page so starred_at is complete.
async function allStargazers() {
  const accept = "application/vnd.github.star+json";
  const stars = [];
  for (let page = 1; page <= 100; page += 1) {
    const batch = await get(`/repos/${repo}/stargazers?per_page=100&page=${page}`, accept);
    if (!Array.isArray(batch) || batch.length === 0) break;
    for (const entry of batch) {
      stars.push({ login: entry?.user?.login ?? null, starred_at: entry?.starred_at ?? null });
    }
    if (batch.length < 100) break;
  }
  return stars;
}

// The registry download count is meaningless before 2.7.6 (no bin shipped, so
// nothing was installable and the traffic was mirrors). Captured from that
// release on as the one number that measures the npm install path directly.
async function npmDownloads(pkg) {
  const range = `https://api.npmjs.org/downloads/range/last-month/${pkg}`;
  const res = await fetch(range, { headers: { "User-Agent": headers["User-Agent"] } });
  if (!res.ok) return null;
  const body = await res.json();
  const daily = body.downloads ?? [];
  const last7 = daily.slice(-7).reduce((sum, d) => sum + d.downloads, 0);
  return { last_7d: last7, last_30d: daily.reduce((s, d) => s + d.downloads, 0), daily };
}

const [meta, views, clones, referrers, paths, releases, stargazers, npm] = await Promise.all([
  get(`/repos/${repo}`),
  get(`/repos/${repo}/traffic/views`),
  get(`/repos/${repo}/traffic/clones`),
  get(`/repos/${repo}/traffic/popular/referrers`),
  get(`/repos/${repo}/traffic/popular/paths`),
  get(`/repos/${repo}/releases?per_page=100`),
  allStargazers(),
  npmDownloads("zero-slop"),
]);

// Clone counts are dominated by mirrors, proxies and scanners: this repo has
// shown ~19 unique cloners per unique viewer. The 10th percentile of the
// trailing daily uniques approximates that automated floor, so subtract it
// before treating clones as a human install signal.
function debiasedClones(series) {
  if (!Array.isArray(series) || series.length === 0) return null;
  const uniques = series.map((d) => d.uniques).sort((a, b) => a - b);
  const floor = uniques[Math.floor(uniques.length * 0.1)] ?? 0;
  const latest = series[series.length - 1];
  return { floor, latest_uniques: latest?.uniques ?? 0, above_floor: Math.max(0, (latest?.uniques ?? 0) - floor) };
}

const row = {
  captured_at: new Date().toISOString(),
  repo,
  stars: meta?.stargazers_count ?? null,
  forks: meta?.forks_count ?? null,
  watchers: meta?.subscribers_count ?? null,
  open_issues: meta?.open_issues_count ?? null,
  views_14d: { total: views?.count ?? null, uniques: views?.uniques ?? null },
  views_daily: views?.views ?? [],
  clones_14d: { total: clones?.count ?? null, uniques: clones?.uniques ?? null },
  clones_daily: clones?.clones ?? [],
  clones_debiased: debiasedClones(clones?.clones),
  referrers: referrers ?? [],
  paths: paths ?? [],
  releases: (releases ?? []).map((r) => ({
    tag: r.tag_name,
    published_at: r.published_at,
    downloads: (r.assets ?? []).reduce((sum, a) => sum + (a.download_count ?? 0), 0),
    // Per asset, because the three install surfaces convert differently: the
    // zip is the claude.ai button, the single file is ChatGPT, the PDF is
    // marketing. One total hides which one is actually working.
    assets: (r.assets ?? []).map((a) => ({ name: a.name, downloads: a.download_count ?? 0 })),
  })),
  npm,
  stargazers_count_walked: stargazers.length,
  stargazers,
};

const fs = await import("node:fs/promises");
await fs.appendFile(out, `${JSON.stringify(row)}\n`, "utf8");

// Star velocity is what GitHub Trending ranks on, so report it every run.
const byDay = new Map();
for (const s of stargazers) {
  if (!s.starred_at) continue;
  const day = s.starred_at.slice(0, 10);
  byDay.set(day, (byDay.get(day) ?? 0) + 1);
}
const days = [...byDay.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1)).slice(0, 7);

console.log(`stars=${row.stars} forks=${row.forks} views14d=${row.views_14d.uniques}u clones_above_floor=${row.clones_debiased?.above_floor ?? "n/a"} npm7d=${npm?.last_7d ?? "n/a"}`);
console.log("stars per day (last 7 with activity):");
for (const [day, n] of days) console.log(`  ${day}  ${"*".repeat(Math.min(n, 60))} ${n}`);
