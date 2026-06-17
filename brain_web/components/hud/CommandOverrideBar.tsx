"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type Props = {
  disabled?: boolean;
  connected?: boolean;
};

export function CommandOverrideBar({ disabled = false, connected = true }: Props) {
  const [commandInput, setCommandInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isDisabled = disabled || sending || !connected;

  async function submitCommand() {
    const text = commandInput.trim();
    if (!text || isDisabled) return;
    setSending(true);
    setError(null);
    setCommandInput("");
    try {
      const res = await api.sendUserPrompt(text);
      if (!res.ok) {
        setError(res.error || "Send failed");
        setCommandInput(text);
      }
    } catch {
      setError("Cannot reach brain API — is the kernel online?");
      setCommandInput(text);
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key !== "Enter") return;
    e.preventDefault();
    void submitCommand();
  }

  return (
    <div className="w-full shrink-0">
      <input
        type="text"
        value={commandInput}
        onChange={(e) => setCommandInput(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={isDisabled}
        placeholder="> Enter manual override command..."
        aria-label="Manual override command"
        className="w-full rounded border border-hud-cyan/20 bg-black/50 px-4 py-3 font-mono text-sm text-hud-cyan placeholder:text-hud-cyan/35 outline-none transition focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/50 disabled:cursor-not-allowed disabled:opacity-50"
      />
      {error ? (
        <p className="mt-1 font-mono text-[10px] text-red-400">{error}</p>
      ) : disabled ? (
        <p className="mt-1 font-mono text-[10px] text-hud-cyan/40">
          Manager processing — input locked
        </p>
      ) : null}
    </div>
  );
}
