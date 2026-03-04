"use client";

import type { Message } from "@/lib/types";

interface Props {
  message: Message;
  isLatest?: boolean;
}

export function MessageBubble({ message, isLatest }: Props) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-2.5 ${isUser ? "justify-end" : "justify-start"} ${
        isLatest ? (isUser ? "animate-slide-right" : "animate-slide-left") : "animate-fade-in"
      }`}
    >
      {/* Assistant avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-[var(--color-rabo)] to-[#e65500] flex items-center justify-center mt-0.5">
          <svg viewBox="0 0 16 16" className="w-3.5 h-3.5 text-white" fill="currentColor">
            <path d="M8 1a7 7 0 100 14A7 7 0 008 1zM5.5 6.5a1 1 0 112 0 1 1 0 01-2 0zm3 0a1 1 0 112 0 1 1 0 01-2 0zM5.25 9.5a.5.5 0 01.7-.08A3.48 3.48 0 008 10.25c.78 0 1.5-.3 2.05-.83a.5.5 0 01.7.71A4.48 4.48 0 018 11.25a4.48 4.48 0 01-2.83-1.04.5.5 0 01-.08-.7h.16z"/>
          </svg>
        </div>
      )}

      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-[14px] leading-relaxed ${
          isUser
            ? "bg-[var(--color-foreground)] text-white rounded-br-lg"
            : "bg-[var(--color-surface)] text-[var(--color-foreground)] border border-[var(--color-border)] rounded-bl-lg shadow-sm"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}
