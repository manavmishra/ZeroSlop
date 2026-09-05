# GitHub discovery and conversion audit

Reviewed 5 September 2026. Star counts are snapshots, not evidence that a
README layout caused a repository's growth.

## The useful pattern

The strongest open-source product pages answer four questions before asking the
visitor to scroll:

1. What does this do?
2. Can I see it work?
3. Can I try it in under a minute?
4. Why should I trust it?

The order is the important part. State the promise, show proof, give the
command, then offer deeper evidence.

## Repositories reviewed

| Repository | Snapshot | What its product page does well | Applied to Zero Slop |
|---|---:|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | ~282k stars | Names the concept immediately, then routes by environment. | One clear promise and environment-specific install routes. |
| [anthropics/skills](https://github.com/anthropics/skills) | ~174k | Explains the artifact before the mechanics and makes installation concrete. | “Agent Skill, not a model” appears before implementation detail. |
| [github/spec-kit](https://github.com/github/spec-kit) | ~134k | Category-defining headline, clear navigation, concrete benefits. | A short top-of-page path for try, install, evidence, and release. |
| [browser-use/browser-use](https://github.com/browser-use/browser-use) | ~112k | Strong visual identity, task examples, one-command quick start. | Branded signature animation, five use cases, one universal command. |
| [astral-sh/uv](https://github.com/astral-sh/uv) | ~90k | Precise claim, proof visual near the top, scannable highlights. | The 18-draft replay is summarized early and qualified in full below. |
| [blader/humanizer](https://github.com/blader/humanizer) | ~43k | Direct description, simple usage, before-and-after examples. | Four reproducible examples covering launch, product, email, and research prose. |

GitHub's own guidance says a README should explain what the project does, why
it is useful, how to get started, where to get help, and who maintains it. It
also recommends moving long documentation out of the README:
[About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes).

## Baseline findings

The repository already had unusually strong technical evidence, privacy
boundaries, releases, and a working one-command installer. The main conversion
problem was hierarchy:

- The first screen led with a slogan and badges before showing a compact,
  source-preserving result.
- The demo ended on a score but did not show the edited sentence.
- The social card said “No rewrites,” which contradicted the product.
- The long benchmark section crowded the path from interest to installation.
- Version and README-score badges were manual and could go stale.
- Several repository topics implied authorship detection even though the
  project explicitly rejects that claim.
- There were no issue forms, pull-request template, contribution guide, support
  guide, or code of conduct.
- Distribution copy still cited an older benchmark result and a 13-star
  baseline.

## Changes applied

### Discovery

- Search language now appears naturally: AI writing, AI editor, writing
  assistant, humanizer, Agent Skill, Claude Code, Codex, ChatGPT, and MCP.
- The repository description and 20 topics have a single recommended spec
  below.
- Dynamic npm, download, CI, star, and license badges replace manual release
  metadata.
- Permanent `releases/latest` asset links remove release-number churn. GitHub
  documents both the latest-release URL and direct latest-asset URLs:
  [Linking to releases](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases).

### Conversion

- The first screen now contains the promise, browser CTA, install command,
  signature animation, and trust line.
- An example moves from 99.3 to 9.5, shows the actual rewrite, and keeps the
  40% detail.
- Installation routes cover local skills, file uploads, Claude.ai, and hosted
  MCP clients.
- The hosted MCP has a clear convenience pitch without blurring the remote
  versus local privacy boundary.
- Secondary benchmarks moved into a disclosure, leaving the primary evidence
  visible.

### Trust and contribution

- Four examples can be rescored and checked for protected strings.
- Structured issue forms request a minimal reproduction and warn against
  posting confidential drafts.
- Contributing, support, conduct, security, discussions, and releases are now
  connected from the README.
- Claims distinguish a heuristic writing meter from authorship detection and
  distinguish regression evidence from field accuracy.

GitHub allows up to 20 repository topics and recommends terms that fit the
project and its intended readers:
[Classifying a repository with topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics).
Issue forms improve the quality of incoming reports by asking for the same
fields each time:
[Issue and pull-request templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates).

## GitHub metadata specification

### Description

> Open-source Agent Skill that scores AI-sounding writing 0–100, edits it with
> your assistant, and checks source details locally.

### Homepage

`https://zero-slop.ai`

### Topics

```text
agent-skills
ai-writing
writing-assistant
writing-tools
ai-editor
editing
prose-linter
ai-slop
anti-slop
humanizer
humanize-ai-text
claude-code
claude-skill
codex
cursor
mcp-server
model-context-protocol
offline-first
privacy
open-source
```

Remove `ai-detection`, `ai-slop-detection`, and `slop-detector`. Those terms
attract the wrong expectation and conflict with the project's stated limits.

### Social preview

Upload `assets/social-preview.png`. It is 1280×640, uses a solid dark base, and
stays below 1 MB, matching GitHub's recommended size and format:
[Customizing a social preview](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview).

## Measurement

Use one weekly snapshot and one launch-day sheet. Track:

| Funnel stage | Measure |
|---|---|
| Discovery | GitHub unique visitors, referring sites, social post views |
| Interest | README-to-site clicks, demo completion where the platform reports it |
| Activation | npm downloads, release downloads, successful install reports |
| Hosted intent | MCP guide visits and copied setup commands, if measured without draft telemetry |
| Retention | Repeat npm usage, returning site visitors, substantive issues and discussions |
| Advocacy | Stars, forks, mentions, directory inclusions, creator posts |

Do not optimize stars alone. The primary outcome is a successful first use; a
star is a useful distribution signal, not the product.
