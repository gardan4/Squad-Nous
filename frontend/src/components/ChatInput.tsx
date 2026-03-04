"use client";

import { FormEvent, useState } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled, placeholder }: Props) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <div className="relative flex-1">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder || "Type a message..."}
          disabled={disabled}
          className="w-full rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-3 text-[14px] text-[var(--color-foreground)] outline-none transition-all placeholder:text-[var(--color-muted-light)] focus:border-[var(--color-rabo)] focus:shadow-[0_0_0_3px_var(--color-rabo-light)] disabled:opacity-50"
          autoFocus
        />
      </div>
      <button
        type="submit"
        disabled={disabled || !input.trim()}
        className="flex-shrink-0 flex items-center justify-center w-11 h-11 rounded-full bg-[var(--color-rabo)] text-white transition-all hover:bg-[#e65500] active:scale-90 disabled:opacity-30 disabled:pointer-events-none"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-4.5 h-4.5">
          <path d="M3.105 2.289a.75.75 0 00-.826.95l1.414 4.925A1.5 1.5 0 005.135 9.25h6.115a.75.75 0 010 1.5H5.135a1.5 1.5 0 00-1.442 1.086l-1.414 4.926a.75.75 0 00.826.95l14.095-5.638a.75.75 0 000-1.392L3.105 2.289z"/>
        </svg>
      </button>
    </form>
  );
}
