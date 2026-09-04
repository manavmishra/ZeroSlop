/* eslint-disable @next/next/no-img-element -- static Cloudflare export uses pre-sized local assets */
import { CopyCommand } from "./CopyCommand";
import { ExampleGallery } from "./ExampleGallery";

const githubUrl = "https://github.com/manavmishra/ZeroSlop";
const releaseUrl = `${githubUrl}/releases/latest`;
const skillVersion = "2.8.10";
const compatibleAgents = [
  "Codex",
  "Claude Code",
  "Cursor",
  "Gemini CLI",
  "OpenCode",
  "Warp",
  "Zed",
];

const faqs = [
  {
    question: "What is AI slop?",
    answer:
      "AI slop is writing that relies on safe phrasing, even rhythm, template structure, stock transitions, and polished sentences that say very little. Zero Slop shows you exactly where those patterns occur.",
  },
  {
    question: "Is Zero Slop an AI detector?",
    answer:
      "No. Detectors estimate whether a machine wrote something. Zero Slop instead finds the AI accent, removes it, and checks figures, names, quotes, and links against the original.",
  },
  {
    question: "Will it change my facts?",
    answer:
      "Zero Slop is designed to prevent that. It inventories figures, names, quotes, and links, then rejects a rewrite that drops one or adds a new one. You still make the final editorial call.",
  },
  {
    question: "Does the scorer send my writing anywhere?",
    answer:
      "No. The scorer is a local Python script that uses only the standard library. It works offline and needs no account, server, or network connection. The skill itself runs inside the coding or writing agent you already use.",
  },
  {
    question: "Where can I use it?",
    answer:
      "Zero Slop works with agents that support SKILL.md files, including Codex, Claude Code, Cursor, Gemini CLI, OpenCode, Warp, and Zed. The repository also documents setup for ChatGPT and claude.ai.",
  },
  {
    question: "Is Zero Slop free?",
    answer:
      "Yes. Zero Slop is open source under the MIT license. The scorer uses only Python's standard library; it needs no third-party packages.",
  },
];

const softwareJsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "@id": "https://zero-slop.ai/#software",
  name: "Zero Slop",
  url: "https://zero-slop.ai/",
  downloadUrl: githubUrl,
  description:
    "An open-source AI writing humanizer and anti-slop checker that scores machine-like writing patterns, rewrites drafts, and checks important details against the original.",
  applicationCategory: "WritingApplication",
  operatingSystem: "Cross-platform",
  isAccessibleForFree: true,
  license: "https://opensource.org/license/mit",
  codeRepository: githubUrl,
  softwareVersion: skillVersion,
  provider: { "@id": "https://zero-slop.ai/#organization" },
  featureList: [
    "AI writing pattern scoring",
    "Meaning-preserving rewrites for social posts, articles, documents, and presentations",
    "Local offline scoring",
    "Checks for changed figures, names, quotes, and links",
  ],
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
};

const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "@id": "https://zero-slop.ai/#faq",
  mainEntity: faqs.map((faq) => ({
    "@type": "Question",
    name: faq.question,
    acceptedAnswer: {
      "@type": "Answer",
      text: faq.answer,
    },
  })),
};

const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  "@id": "https://zero-slop.ai/#organization",
  name: "Zero Slop",
  url: "https://zero-slop.ai/",
  logo: "https://zero-slop.ai/favicon.svg",
  sameAs: [githubUrl],
};

const websiteJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  "@id": "https://zero-slop.ai/#website",
  name: "Zero Slop",
  alternateName: "Zero Slop AI Writing Humanizer",
  url: "https://zero-slop.ai/",
  description:
    "A free, open-source AI writing humanizer and anti-slop checker with local scoring and checks against the original.",
  publisher: { "@id": "https://zero-slop.ai/#organization" },
  about: { "@id": "https://zero-slop.ai/#software" },
  inLanguage: "en-US",
};

const howToJsonLd = {
  "@context": "https://schema.org",
  "@type": "HowTo",
  "@id": "https://zero-slop.ai/#how-to",
  name: "How to remove AI writing patterns with Zero Slop",
  description:
    "Install Zero Slop, ask your writing agent to revise a draft, then review its score and compare the rewrite with the original.",
  supply: [{ "@type": "HowToSupply", name: "A draft to revise" }],
  tool: [{ "@type": "HowToTool", name: "A compatible writing or coding agent" }],
  step: [
    {
      "@type": "HowToStep",
      name: "Install Zero Slop",
      text: "Run npx skills add manavmishra/ZeroSlop --global in your terminal.",
      url: "https://zero-slop.ai/#install",
    },
    {
      "@type": "HowToStep",
      name: "Rewrite the draft",
      text: "Give the draft to a compatible agent and ask it to use Zero Slop.",
      url: "https://zero-slop.ai/#how-it-works",
    },
    {
      "@type": "HowToStep",
      name: "Review the proof",
      text: "Check the before-and-after scores, read the rewrite aloud, and compare it with the original before publishing.",
      url: "https://zero-slop.ai/#proof",
    },
  ],
};

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>

      <header className="site-header">
        <a className="wordmark" href="#top">
          <span aria-hidden="true" className="wordmark-mark">
            ZS
          </span>
          <span>Zero Slop</span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#examples">Examples</a>
          <a href="#how-it-works">How it works</a>
          <a href="#proof">Proof</a>
          <a href="#install">Install</a>
          <a href={githubUrl} target="_blank" rel="noreferrer">
            GitHub
          </a>
        </nav>
      </header>

      <main id="main-content">
        <section className="hero section-shell" id="top">
          <div className="hero-copy">
            <p className="eyebrow">Open source · v{skillVersion} · local scoring</p>
            <h1>Make AI writing sound like you.</h1>
            <p className="hero-lede">
              Zero Slop finds the AI accent, rewrites your draft, and checks
              figures, names, quotes, and links against the original.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="#install">
                Install
              </a>
              <a
                className="button button-secondary"
                href={githubUrl}
                target="_blank"
                rel="noreferrer"
              >
                GitHub
              </a>
            </div>
          </div>

          <figure className="hero-visual">
            <div className="visual-bar" aria-hidden="true">
              <span>draft.md</span>
              <span>lower is better</span>
            </div>
            <picture>
              <source
                type="image/avif"
                srcSet="/demo-384.avif 384w, /demo-750.avif 750w, /demo.avif 1500w"
                sizes="(max-width: 767px) calc(100vw - 32px), 54vw"
              />
              <img
                src="/demo.png"
                alt="Zero Slop gives an AI-heavy sentence a writing score of 100 and its clearer rewrite a score of 9.5"
                width="1500"
                height="800"
                loading="eager"
                fetchPriority="high"
                decoding="async"
              />
            </picture>
          </figure>
        </section>

        <section className="metrics section-shell" aria-label="Project facts">
          <div>
            <strong>CI</strong>
            <span>gated checks</span>
          </div>
          <div>
            <strong>0</strong>
            <span>third-party scorer packages</span>
          </div>
          <div>
            <strong>Offline</strong>
            <span>scoring available</span>
          </div>
          <div>
            <strong>MIT</strong>
            <span>open-source license</span>
          </div>
        </section>

        <section className="intro section-shell section-block">
          <p className="section-kicker">The facts come first.</p>
          <h2>Score the slop. Keep the meaning.</h2>
          <p>
            A rewrite can remove stock phrases and still fail if it fakes
            candor, chops every sentence short, or invents details. Zero Slop
            fixes the wording without changing what the draft says.
          </p>
        </section>

        <section
          className="examples section-shell section-block"
          id="examples"
          aria-labelledby="examples-title"
        >
          <div className="examples-heading">
            <h2 id="examples-title">See what changes.</h2>
            <p>
              Switch formats to compare an AI-heavy draft with a tighter rewrite.
              The main claim stays put.
            </p>
          </div>
          <ExampleGallery />
        </section>

        <section
          className="method section-shell section-block"
          id="how-it-works"
          aria-labelledby="method-title"
        >
          <div className="section-heading">
            <h2 id="method-title">Eight roles. Two loops. One clean handoff.</h2>
            <p>
              Local tools handle repeatable checks. The AI already running in
              your assistant handles context and editing. Each role has one job,
              and any repair goes back through the final editorial passes.
            </p>
          </div>

          <figure className="engine-diagram">
            <img
              src="/engine.svg"
              alt="Zero Slop moves a draft through eight editorial roles, ending with a fresh-eyes finalizer that reads the verified text as a first-time reader, learns privately only from before-and-after versions supplied by the writer, and evaluates shared changes in a separate release review"
              width="1600"
              height="900"
              loading="lazy"
              decoding="async"
            />
            <figcaption>
              Loop 1 finishes the current draft. Loop 2 learns only from edits
              you provide. Release review stays separate from both.
            </figcaption>
          </figure>
        </section>

        <section
          className="proof section-shell section-block"
          id="proof"
          aria-labelledby="proof-title"
        >
          <div className="proof-copy">
            <h2 id="proof-title">Fresh scores. Public inputs.</h2>
            <p>
              Version {skillVersion} rescored the pinned RAID+ sample and regenerated
              four editing workflows on the same 18 drafts with GPT-5.4. A separate
              two-pass review then hid the method names and reshuffled the A/B order:
              the reviewer favoured Zero Slop on 13 drafts and avoid-ai-writing on 3,
              with both passes agreeing on 16 of 18. The inputs, hashes, results, and
              limits are public. RAID+ records model origin, not editorial quality.
            </p>
            <a
              className="text-link"
              href={`${githubUrl}#what-the-current-release-measured`}
              target="_blank"
              rel="noreferrer"
            >
              Read the benchmark notes
            </a>
          </div>

          <div className="proof-gallery">
            <figure>
              <img
                src="/bench-raid-plus.png"
                alt="Mean Zero Slop writing scores for 7,627 non-empty RAID+ abstracts: DeepSeek V3 14.5, Gemini 3.1 Pro 17.0, Gemma 3 27B 21.6, and Llama 3.3 70B 25.5"
                width="1240"
                height="374"
                loading="lazy"
                decoding="async"
              />
              <figcaption>All usable RAID+ rows at the pinned revision; not an accuracy claim.</figcaption>
            </figure>
            <figure className="proof-secondary">
              <img
                src="/bench-search-rewrites.png"
                alt="Fresh same-model editing replay on 18 drafts: Zero Slop 12.8, avoid-ai-writing 23.3, no-ai-slop 28.4, and humanizer 35.4"
                width="1240"
                height="478"
                loading="lazy"
                decoding="async"
              />
              <figcaption>Fresh GPT-5.4 rewrites with the same model settings; Zero Slop&apos;s meter, not independent human accuracy.</figcaption>
            </figure>
            <figure className="proof-secondary">
              <img
                src="/bench-incumbent-hidden.png"
                alt="Two-pass method-hidden editorial review of 18 drafts: the reviewer favoured Zero Slop on 13 drafts and avoid-ai-writing on 3, with 2 unresolved"
                width="1240"
                height="478"
                loading="lazy"
                decoding="async"
              />
              <figcaption>Method names hidden and A/B order reshuffled between passes; a small LLM-reviewed comparison, not human field accuracy.</figcaption>
            </figure>
            <figure className="proof-secondary">
              <img
                src="/competitor-capabilities.png"
                alt="Documented capabilities across five open-source anti-slop projects at pinned commits, covering detection reporting, a numeric meter, fact checking, separate editorial gates, private learning, and obfuscation-resistant matching"
                width="1240"
                height="720"
                loading="lazy"
                decoding="async"
              />
              <figcaption>Repository audit at pinned commits. It records documented features, not which tool writes better.</figcaption>
            </figure>
          </div>
        </section>

        <section className="honesty section-shell section-block" aria-labelledby="honesty-title">
          <div className="honesty-statement">
            <h2 id="honesty-title">Context comes before a score.</h2>
            <p>
              One em dash does not make a draft machine-written. Formal prose is
              not automatically AI-made. Zero Slop weighs patterns, not isolated
              signals.
            </p>
          </div>
          <div className="honesty-notes">
            <article>
              <h3>The rewrite is checked against the original</h3>
              <p>Before a rewrite passes, Zero Slop checks every figure, name, quote, and link for additions or omissions.</p>
            </article>
            <article>
              <h3>Your words are not automatic red flags</h3>
              <p>
                Add a writing sample to create a private profile of existing watchlist words you use.
                One exact match is enough. The scorer ignores them only when that profile is selected;
                it does not learn your voice or full writing style.
              </p>
            </article>
          </div>
        </section>

        <section
          className="install section-shell section-block"
          id="install"
          aria-labelledby="install-title"
        >
          <div className="install-copy">
            <p className="section-kicker">Works where you write.</p>
            <h2 id="install-title">One skill. Your compatible agent.</h2>
            <p>
              Install Zero Slop in Codex, Claude Code, Cursor, Gemini CLI,
              OpenCode, Warp, or Zed. It also works in any agent that reads
              SKILL.md files.
            </p>
            <div className="install-actions">
              <a className="button button-primary" href={githubUrl} target="_blank" rel="noreferrer">
                Read the setup guide
              </a>
              <a className="button button-secondary" href={releaseUrl} target="_blank" rel="noreferrer">
                Latest release
              </a>
            </div>
          </div>

          <div className="install-workspace">
            <div className="install-workspace-bar" aria-hidden="true">
              <span>Terminal</span>
              <span>one skill, eight roles</span>
            </div>
            <CopyCommand />
            <div className="compatibility-map">
              <div className="skill-file">
                <span className="skill-file-mark" aria-hidden="true">ZS</span>
                <strong>SKILL.md</strong>
                <p>Zero Slop&apos;s scoring, rewrite, and copy-desk instructions</p>
              </div>
              <div className="agent-board">
                <p>Compatible agents</p>
                <ul aria-label="Compatible agents">
                  {compatibleAgents.map((agent) => (
                    <li key={agent}>{agent}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section className="faq section-shell section-block" aria-labelledby="faq-title">
          <div className="faq-heading">
            <h2 id="faq-title">Questions, answered plainly.</h2>
            <p>What the tool does, where it runs, and what it costs.</p>
          </div>
          <div className="faq-list">
            {faqs.map((faq) => (
              <details key={faq.question}>
                <summary>{faq.question}</summary>
                <p>{faq.answer}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="closing section-shell section-block" aria-labelledby="closing-title">
          <p>Lower is better.</p>
          <h2 id="closing-title">Keep the part only you could have written.</h2>
          <div className="hero-actions">
            <a className="button button-primary" href="#install">
              Install
            </a>
            <a
              className="button button-secondary"
              href={githubUrl}
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
          </div>
        </section>
      </main>

      <footer className="site-footer section-shell">
        <a className="wordmark" href="#top">
          <span aria-hidden="true" className="wordmark-mark">ZS</span>
          <span>Zero Slop</span>
        </a>
        <p>Open source under the MIT license.</p>
        <div>
          <a href={githubUrl} target="_blank" rel="noreferrer">GitHub</a>
          <a href={releaseUrl} target="_blank" rel="noreferrer">Releases</a>
        </div>
      </footer>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(howToJsonLd) }}
      />
    </>
  );
}
