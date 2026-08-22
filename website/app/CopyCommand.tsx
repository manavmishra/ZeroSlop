const command = "npx skills add manavmishra/ZeroSlop --global";

const copyScript = String.raw`(() => {
  const root = document.currentScript?.closest("[data-copy-command]");
  if (!root || root.dataset.ready === "true") return;
  root.dataset.ready = "true";
  const button = root.querySelector("button");
  const live = root.querySelector('[aria-live="polite"]');
  let resetTimer;
  button?.addEventListener("click", async () => {
    window.clearTimeout(resetTimer);
    try {
      await navigator.clipboard.writeText("npx skills add manavmishra/ZeroSlop --global");
      button.textContent = "Copied";
      live.textContent = "Install command copied to clipboard.";
    } catch {
      button.textContent = "Copy failed";
      live.textContent = "The install command could not be copied. Select the command and copy it manually.";
    }
    resetTimer = window.setTimeout(() => {
      button.textContent = "Copy";
      live.textContent = "";
    }, 2400);
  });
})();`;

export function CopyCommand() {
  return (
    <div className="command-shell" data-copy-command>
      <code>
        <span aria-hidden="true">$ </span>
        {command}
      </code>
      <button
        className="copy-button"
        type="button"
        aria-label="Copy the Zero Slop install command"
      >
        Copy
      </button>
      <span className="sr-only" aria-live="polite" />
      <script data-zero-slop-ui dangerouslySetInnerHTML={{ __html: copyScript }} />
    </div>
  );
}
