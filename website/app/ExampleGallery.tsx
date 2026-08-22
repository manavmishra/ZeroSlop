type SampleCopy = {
  title?: string;
  paragraphs?: string[];
  bullets?: string[];
};

type Example = {
  id: string;
  label: string;
  format: string;
  file: string;
  layout: "prose" | "document" | "thread" | "slide";
  beforeScore: string;
  afterScore: string;
  before: SampleCopy;
  after: SampleCopy;
};

const examples: Example[] = [
  {
    id: "linkedin",
    label: "LinkedIn post",
    format: "LI",
    file: "launch-post.txt",
    layout: "prose",
    beforeScore: "100.0",
    afterScore: "9.5",
    before: {
      paragraphs: [
        "We’re thrilled to announce that our team has leveraged cutting-edge AI to deliver a seamless onboarding experience, cutting setup time by 40%. This milestone underscores our unwavering commitment to innovation and operational excellence.",
      ],
    },
    after: {
      paragraphs: ["We cut onboarding setup time by 40% using AI."],
    },
  },
  {
    id: "blog",
    label: "Blog intro",
    format: "WEB",
    file: "editorial-intro.md",
    layout: "prose",
    beforeScore: "99.8",
    afterScore: "11.5",
    before: {
      paragraphs: [
        "In today’s rapidly evolving landscape, AI is enabling content teams to accelerate the drafting process while maintaining authenticity. In this article, we’ll explore how thoughtful review workflows can bridge the gap and empower writers to create meaningful content.",
      ],
    },
    after: {
      paragraphs: [
        "AI helps content teams draft faster without losing their voice. This article looks at review workflows that protect authenticity and help writers produce work that matters.",
      ],
    },
  },
  {
    id: "strategy",
    label: "Strategy document",
    format: "DOC",
    file: "operating-model.doc",
    layout: "document",
    beforeScore: "96.7",
    afterScore: "17.6",
    before: {
      paragraphs: [
        "To unlock scalable value, the organization should leverage a comprehensive, cross-functional transformation framework that aligns AI-enabled operating models with strategic priorities.",
        "This integrated approach will empower teams to optimize decision-making and drive sustainable impact across the enterprise.",
      ],
    },
    after: {
      paragraphs: [
        "The organization should use one cross-functional plan to align its AI operating models with its priorities.",
        "That plan should help teams make better decisions and create lasting value.",
      ],
    },
  },
  {
    id: "thread",
    label: "X thread",
    format: "X",
    file: "writing-thread.txt",
    layout: "thread",
    beforeScore: "93.5",
    afterScore: "17.7",
    before: {
      paragraphs: [
        "AI is transforming how we write, but here’s what nobody tells you: the future isn’t about replacing writers.",
        "It’s about leveraging AI to accelerate the drafting process while unlocking the unique human creativity that makes great writing possible. A thread 🧵",
      ],
    },
    after: {
      paragraphs: [
        "AI can speed up drafting without replacing writers.",
        "Human creativity still makes great writing possible.",
      ],
    },
  },
  {
    id: "powerpoint",
    label: "PowerPoint slide",
    format: "PPT",
    file: "sales-cycle.ppt",
    layout: "slide",
    beforeScore: "100.0",
    afterScore: "9.5",
    before: {
      title: "Unlocking Next-Generation Commercial Excellence",
      bullets: [
        "Leverage cutting-edge, AI-enabled workflows to seamlessly streamline the sales cycle.",
        "Utilize a shared account brief to foster cross-functional alignment.",
        "Drive sustainable growth by measuring lead-to-contract time.",
      ],
    },
    after: {
      title: "Shorten the sales cycle with AI",
      bullets: [
        "Use one account brief across teams.",
        "Measure lead-to-contract time to support lasting growth.",
      ],
    },
  },
];

const galleryScript = String.raw`(() => {
  const root = document.currentScript?.closest("[data-example-gallery]");
  if (!root || root.dataset.ready === "true") return;
  root.dataset.ready = "true";
  const tabs = [...root.querySelectorAll('[role="tab"]')];
  const panels = [...root.querySelectorAll('[role="tabpanel"]')];
  const activate = (index, moveFocus = false) => {
    tabs.forEach((tab, tabIndex) => {
      const selected = tabIndex === index;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    panels.forEach((panel, panelIndex) => {
      panel.hidden = panelIndex !== index;
    });
    if (moveFocus) tabs[index]?.focus();
  };
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(index));
    tab.addEventListener("keydown", (event) => {
      let nextIndex = index;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") nextIndex = 0;
      else if (event.key === "End") nextIndex = tabs.length - 1;
      else return;
      event.preventDefault();
      activate(nextIndex, true);
    });
  });
})();`;

function CopySurface({
  sample,
  example,
  side,
}: {
  sample: SampleCopy;
  example: Example;
  side: "before" | "after";
}) {
  return (
    <article className={`sample-surface sample-${example.layout} sample-${side}`}>
      <div className="sample-fileline">
        <span aria-hidden="true">{example.format}</span>
        <span>{example.file}</span>
      </div>
      <div className="sample-copy">
        {sample.title ? <h4>{sample.title}</h4> : null}
        {sample.paragraphs?.map((paragraph, index) => (
          <div className="sample-paragraph" key={paragraph}>
            {example.layout === "thread" ? (
              <span className="thread-index" aria-hidden="true">
                {index + 1}/{sample.paragraphs?.length}
              </span>
            ) : null}
            <p>{paragraph}</p>
          </div>
        ))}
        {sample.bullets ? (
          <ul>
            {sample.bullets.map((bullet) => (
              <li key={bullet}>{bullet}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </article>
  );
}

export function ExampleGallery() {
  return (
    <div className="example-workbench" data-example-gallery>
      <div className="example-workbench-bar">
        <span>Sample rewrites</span>
        <span>lower is better</span>
      </div>

      <div className="example-tabs-wrap">
        <div className="example-tabs" role="tablist" aria-label="Writing format examples">
          {examples.map((example, index) => (
            <button
              role="tab"
              aria-controls={`example-panel-${example.id}`}
              aria-selected={index === 0}
              id={`example-tab-${example.id}`}
              key={example.id}
              tabIndex={index === 0 ? 0 : -1}
              type="button"
            >
              <span aria-hidden="true">{example.format}</span>
              {example.label}
            </button>
          ))}
        </div>
      </div>

      {examples.map((example, index) => (
        <div
          aria-labelledby={`example-tab-${example.id}`}
          className="example-panel"
          hidden={index !== 0}
          id={`example-panel-${example.id}`}
          key={example.id}
          role="tabpanel"
          tabIndex={0}
        >
          <div className="example-pane">
            <header>
              <span>Before</span>
              <span className="sample-score sample-score-before">
                <strong>{example.beforeScore}</strong>
                <span>/100</span>
              </span>
            </header>
            <CopySurface sample={example.before} example={example} side="before" />
          </div>

          <div className="rewrite-mark" aria-hidden="true">
            <span />
            <b>to</b>
            <span />
          </div>

          <div className="example-pane">
            <header>
              <span>After</span>
              <span className="sample-score sample-score-after">
                <strong>{example.afterScore}</strong>
                <span>/100</span>
              </span>
            </header>
            <CopySurface sample={example.after} example={example} side="after" />
          </div>
        </div>
      ))}

      <p className="example-note">
        The sample scores come from the open-source Zero Slop scorer. Each rewrite keeps the main claim from its draft.
      </p>
      <script data-zero-slop-ui dangerouslySetInnerHTML={{ __html: galleryScript }} />
    </div>
  );
}
