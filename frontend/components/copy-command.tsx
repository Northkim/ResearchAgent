"use client";

import { useState } from "react";

export function sanitizeCommand(command: string): string {
  return command
    .replace(/\u00a0/g, " ")
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201c\u201d]/g, '"')
    .replace(/[\u2013\u2014]/g, "-")
    .replace(/\u2028|\u2029/g, "\n")
    .trim();
}

export function CopyCommand({
  command,
  label,
}: {
  command: string;
  label: string;
}) {
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");
  const safeCommand = sanitizeCommand(command);

  async function copy() {
    try {
      await navigator.clipboard.writeText(safeCommand);
      setStatus("copied");
      window.setTimeout(() => setStatus("idle"), 2_000);
    } catch {
      setStatus("failed");
    }
  }

  return (
    <div className="copy-command">
      <code>{safeCommand}</code>
      <button
        type="button"
        className="button button-ghost"
        aria-label={`Copy ${label}`}
        onClick={copy}
      >
        {status === "copied" ? "Copied" : status === "failed" ? "Retry copy" : "Copy"}
      </button>
      <span className="sr-only" role="status" aria-live="polite">
        {status === "copied"
          ? `${label} copied`
          : status === "failed"
            ? `Copy failed. Select the visible ${label} and copy it manually.`
            : ""}
      </span>
    </div>
  );
}
