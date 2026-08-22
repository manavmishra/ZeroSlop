"use client";

import { useEffect, useState } from "react";

const command = "npx skills add manavmishra/ZeroSlop --global";

type CopyState = "idle" | "copied" | "error";

export function CopyCommand() {
  const [copyState, setCopyState] = useState<CopyState>("idle");

  useEffect(() => {
    if (copyState === "idle") return;
    const timer = window.setTimeout(() => setCopyState("idle"), 2400);
    return () => window.clearTimeout(timer);
  }, [copyState]);

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(command);
      setCopyState("copied");
    } catch {
      setCopyState("error");
    }
  }

  const label =
    copyState === "copied"
      ? "Copied"
      : copyState === "error"
        ? "Copy failed"
        : "Copy";

  return (
    <div className="command-shell">
      <code>
        <span aria-hidden="true">$ </span>
        {command}
      </code>
      <button
        className="copy-button"
        type="button"
        onClick={copyCommand}
        aria-label="Copy the Zero Slop install command"
      >
        {label}
      </button>
      <span className="sr-only" aria-live="polite">
        {copyState === "copied"
          ? "Install command copied to clipboard."
          : copyState === "error"
            ? "The install command could not be copied. Select the command and copy it manually."
            : ""}
      </span>
    </div>
  );
}
