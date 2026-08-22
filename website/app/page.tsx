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
      "The fidelity check is designed to prevent that. It inventories figures, names, quotes, and links, then fails if the rewrite drops one or introduces a new one. You still make the final editorial call.",
  },
  {
    question: "Does the scorer send my writing anywhere?",
    answer:
      "No. The scorer is a local Python script that uses only the standard library; it works offline and needs no account, server, or network connection. The skill itself runs inside the coding or writing agent you already use.",
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
  featureList: [
    "AI writing pattern scoring",
    "Faithful rewrites for social posts, articles, documents, and presentations",
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
  mainEntity: faqs.map((faq) => ({
    "@type": "Question",
    name: faq.question,
    acceptedAnswer: {
      "@type": "Answer",
      text: faq.answer,
    },
  })),
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
                alt="Zero Slop scores an AI-heavy sentence at 100 and its faithful rewrite at 9.5"
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
            <strong>75</strong>
            <span>tests passing</span>
          </div>
          <div>
            <strong>0</strong>
            <span>third-party packages</span>
          </div>
          <div>
            <strong>No</strong>
            <span>network required</span>
          </div>
          <div>
            <strong>MIT</strong>
            <span>open-source license</span>
          </div>
        </section>

        <section className="intro section-shell section-block">
          <p className="section-kicker">Fidelity comes first.</p>
          <h2>Score the slop. Keep the meaning.</h2>
          <p>
            A rewrite can remove stock phrases and still fail if it fakes
            candor, chops every sentence short, or invents details. Zero Slop changes
            the surface and protects the substance.
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
            <h2 id="method-title">The score has four inputs.</h2>
            <p>
              Swapping synonyms cannot fix the structure of a draft. Zero Slop
              checks both its language and its shape.
            </p>
          </div>

          <div className="method-grid">
            <article className="method-feature">
              <p className="method-name">Pattern meter</p>
              <h3>It points to the exact phrase.</h3>
              <p>
                The scorer checks 266 tell patterns, a 96-term watchlist, and
                context-sensitive terms scored only when the surrounding
                sentence makes them suspicious.
              </p>
              <div className="signal-sample" aria-label="Example pattern finding">
                <span>weighted tell</span>
                <mark>generic sales phrase</mark>
              </div>
            </article>

            <article className="method-card rhythm-card">
              <p className="method-name">Rhythm</p>
              <h3>Sentence length should breathe.</h3>
              <div className="rhythm-bars" aria-hidden="true">
                <span />
                <span />
                <span />
                <span />
                <span />
                <span />
              </div>
            </article>

            <article className="method-card reading-card">
              <p className="method-name">Readability</p>
              <h3>It unpacks dense prose.</h3>
              <p>The scorer flags comma pileups, clusters of long words, and sentences of 38 words or more.</p>
            </article>

            <article className="method-card format-card">
              <p className="method-name">Formatting</p>
              <h3>Formatting has tells too.</h3>
              <p>Emoji, hashtag clusters, heavy bolding, and repeated em dashes count when they form a pattern.</p>
            </article>
          </div>
        </section>

        <section className="process section-block" aria-labelledby="process-title">
          <div className="section-shell process-inner">
            <div>
              <h2 id="process-title">Rewrite, then prove it.</h2>
              <p>
                Zero Slop removes stock language, revises the structure and
                wording, then checks the result against the original.
              </p>
            </div>
            <ol className="process-list">
              <li>
                <span>Measure</span>
                <p>Record the tells, rhythm, formatting, and readability before editing.</p>
              </li>
              <li>
                <span>Rewrite</span>
                <p>Keep every claim while changing the language that carries it.</p>
              </li>
              <li>
                <span>Verify</span>
                <p>Re-score the draft, read it aloud, and run the fidelity check.</p>
              </li>
            </ol>
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
                  alt="AI-register scores after rewriting: Zero Slop 10.6, below comparison tools ranging from 16.7 to 28.2"
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
              One phrase can affect the score, but it is not enough to judge a
              draft. Zero Slop considers patterns across the full draft and does
              not penalize formal writing merely for being formal.
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
            <h2 id="install-title">One install. Every compatible agent.</h2>
            <p>
              Install Zero Slop once, then use it in Codex, Claude Code, Cursor,
              Gemini CLI, OpenCode, Warp, or Zed. It also works in any agent that
              reads SKILL.md files.
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
    </>
  );
}
