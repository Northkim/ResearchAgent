"use client";

import { useState } from "react";

export function CopyCommand({
  command,
  label,
}: {
  command: string;
  label: string;
}) {
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");

  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setStatus("copied");
      window.setTimeout(() => setStatus("idle"), 2_000);
    } catch {
      setStatus("failed");
    }
  }

  return (
    <div className="copy-command">
      <code>{command}</code>
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
