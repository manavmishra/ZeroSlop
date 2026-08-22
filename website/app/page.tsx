import { CopyCommand } from "./CopyCommand";
import { ExampleGallery } from "./ExampleGallery";

const githubUrl = "https://github.com/manavmishra/ZeroSlop";
const releaseUrl = `${githubUrl}/releases/latest`;
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
      "AI slop is writing that falls into familiar model habits: safe phrasing, even rhythm, template structure, stock transitions, and polished sentences that say very little. Zero Slop measures those surface patterns and shows you exactly where they occur.",
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
    "An open-source AI writing humanizer and anti-slop checker that scores machine-like writing patterns, rewrites drafts, and verifies factual fidelity.",
  applicationCategory: "WritingApplication",
  operatingSystem: "Cross-platform",
  isAccessibleForFree: true,
  license: "https://opensource.org/license/mit",
  codeRepository: githubUrl,
  provider: { "@id": "https://zero-slop.ai/#organization" },
  featureList: [
    "AI writing pattern scoring",
    "Meaning-preserving rewrites for social posts, articles, documents, and presentations",
    "Local offline scoring",
    "Figure, name, quote, and link fidelity checks",
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
    "A free, open-source AI writing humanizer and anti-slop checker with local scoring and factual fidelity checks.",
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
            <p className="eyebrow">Open source with local scoring</p>
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
                alt="Zero Slop gives an AI-heavy sentence a surface score of 100 and its clearer rewrite a score of 9.5"
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
            <h2 id="method-title">The meter is only one layer.</h2>
            <p>
              Zero Slop pairs traceable local checks with the language model
              already running in your agent. The meter finds evidence. The model
              interprets the draft and edits it.
            </p>
          </div>

          <div
            className="system-map"
            aria-label="Zero Slop implementation layers"
          >
            <article className="system-layer meter-layer">
              <div className="system-layer-heading">
                <p className="method-name">Deterministic measurement</p>
                <span>Local Python</span>
              </div>
              <h3>Find traceable surface evidence.</h3>
              <p>
                The scorer checks 267 weighted patterns. Separate channels
                measure rhythm, density, formatting, and register. The result
                includes quoted spans and document statistics, not an authorship
                probability.
              </p>
              <div className="meter-output" aria-label="Example local scorer output">
                <span>surface evidence</span>
                <strong>quoted phrase</strong>
                <span>sentence statistics</span>
              </div>
            </article>

            <div className="system-connector" aria-hidden="true">
              <span>guides</span>
              <b>→</b>
            </div>

            <article className="system-layer agent-layer">
              <div className="system-layer-heading">
                <p className="method-name">Contextual AI editing</p>
                <span>Host model</span>
              </div>
              <h3>Interpret the draft before changing it.</h3>
              <p>
                Claude, GPT, or another host model evaluates substance, claims,
                structure, audience, and voice. It rewrites and copy-edits the
                draft, then reads it aloud and fixes its flow.
              </p>
              <ul className="agent-checks">
                <li>Meaning and factual scope</li>
                <li>Structure and audience</li>
                <li>Voice and spoken flow</li>
              </ul>
            </article>

            <div className="system-connector" aria-hidden="true">
              <span>checks</span>
              <b>→</b>
            </div>

            <article className="system-layer gate-layer">
              <div className="system-layer-heading">
                <p className="method-name">Final verification</p>
                <span>Scripts + model</span>
              </div>
              <h3>Check the exact text you receive.</h3>
              <p>
                Scripts recheck the score, figures, names, quotations, and links.
                The model rechecks meaning, qualifiers, voice, format, and flow.
                Any change to the text sends it through both editorial passes
                and every final check again.
              </p>
            </article>

            <aside className="learning-return">
              <div>
                <p className="method-name">Private feedback loop</p>
                <h3>Published edits can improve the next run.</h3>
                <p>
                  Human edits can adjust local detector weights and save preferred
                  fixes only after the evidence passes recurrence, novelty, and
                  known-human safety checks. This does not retrain the host model.
                </p>
              </div>
              <div className="learning-path" aria-label="Private learning path">
                <span>Published edit</span>
                <b aria-hidden="true">→</b>
                <span>Evidence checks</span>
                <b aria-hidden="true">→</b>
                <span>Private overlay</span>
                <b aria-hidden="true">→</b>
                <span>Next draft</span>
              </div>
            </aside>
          </div>
        </section>

        <section className="process section-block" aria-labelledby="process-title">
          <div className="section-shell process-inner">
            <div>
              <h2 id="process-title">Two loops. One finished draft.</h2>
              <p>
                The editorial loop finishes today&apos;s draft. The private learning
                loop uses reviewed edits to improve detection and fixing on the
                next run.
              </p>
            </div>
            <div className="process-loops">
              <div>
                <p className="process-label">Loop 1: Editorial delivery</p>
                <ol className="process-list">
                  <li>
                    <span>Measure and diagnose</span>
                    <p>Find the tells, rhythm, formatting, and readability problems.</p>
                  </li>
                  <li>
                    <span>Rewrite and copy edit</span>
                    <p>Keep the substance, rebuild weak passages, and correct the mechanics.</p>
                  </li>
                  <li>
                    <span>Read aloud and verify</span>
                    <p>Fix spoken flow, then recheck the final text against the original.</p>
                  </li>
                </ol>
              </div>
              <div>
                <p className="process-label">Loop 2: Online learning</p>
                <ol className="process-list">
                  <li>
                    <span>Observe and gate</span>
                    <p>Compare reviewed, published edits and require repeated evidence.</p>
                  </li>
                  <li>
                    <span>Update privately</span>
                    <p>Adjust detector weights and save recurring human fixes for the next run.</p>
                  </li>
                  <li>
                    <span>Reconfirm or decay</span>
                    <p>Keep useful guidance current and retire stale local rules.</p>
                  </li>
                </ol>
              </div>
            </div>
          </div>
        </section>

        <section
          className="proof section-shell section-block"
          id="proof"
          aria-labelledby="proof-title"
        >
          <div className="proof-copy">
            <h2 id="proof-title">The benchmark is public.</h2>
            <p>
              The benchmark covers 50 AI-heavy drafts in six kinds of writing,
              compares four tools, and uses blind judging. The repository
              includes both the data and the study&apos;s limitations, so you can
              check the headline yourself.
            </p>
            <a
              className="text-link"
              href={`${githubUrl}#does-it-actually-work`}
              target="_blank"
              rel="noreferrer"
            >
              Read the benchmark notes
            </a>
          </div>

          <div className="proof-gallery">
            <figure>
              <picture>
                <source type="image/avif" srcSet="/bench-bestpicks.avif" />
                <img
                  src="/bench-bestpicks.png"
                  alt="Blind best-pick results across 100 judgments: Zero Slop, 55; blader, 40; no-ai-slop, 5; and de-slop, 0"
                  width="1240"
                  height="374"
                  loading="lazy"
                  decoding="async"
                />
              </picture>
              <figcaption>Results from 100 blind judgments.</figcaption>
            </figure>
            <figure className="proof-secondary">
              <picture>
                <source type="image/avif" srcSet="/bench-detector.avif" />
                <img
                  src="/bench-detector.png"
                  alt="AI-register scores after rewriting: Zero Slop scored 10.6, below comparison tools ranging from 16.7 to 28.2"
                  width="1240"
                  height="530"
                  loading="lazy"
                  decoding="async"
                />
              </picture>
              <figcaption>AI-register scores after rewriting. Lower is cleaner.</figcaption>
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
              <h3>Your habits count</h3>
              <p>Add a sample of your writing so the scorer can recognize which habits belong to you.</p>
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
              <span>one skill, seven agents</span>
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
