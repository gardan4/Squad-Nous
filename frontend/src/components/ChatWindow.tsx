"use client";

import { useEffect, useRef } from "react";
import { useChat } from "@/hooks/useChat";
import { useSchema } from "@/hooks/useSchema";
import type { FieldInfo } from "@/lib/types";
import { ChatInput } from "./ChatInput";
import { CompletionView } from "./CompletionView";
import { FieldProgress } from "./FieldProgress";
import { InlineCarSelector } from "./InlineCarSelector";
import { MessageBubble } from "./MessageBubble";
import { QuickReplies } from "./QuickReplies";
import { SessionStatus } from "./SessionStatus";
import { SummaryCard } from "./SummaryCard";

function detectCurrentField(
  fields: FieldInfo[] | undefined,
  extractedFields: Record<string, unknown>,
  lastMessage: string | undefined
): FieldInfo | null {
  if (!fields || !lastMessage) return null;

  // Find fields that haven't been collected yet
  const remaining = fields.filter(
    (f) => extractedFields[f.name] === undefined || extractedFields[f.name] === ""
  );

  if (remaining.length === 0) return null;

  // Try to match the assistant's last message to a field
  const msg = lastMessage.toLowerCase();
  for (const field of remaining) {
    const keywords: Record<string, string[]> = {
      car_type: ["type of car", "car type", "what type", "sedan", "coupe", "hatchback", "minivan", "station wagon"],
      manufacturer: ["manufacturer", "brand", "make", "who makes"],
      year_of_construction: ["year", "when was", "manufactured", "construction"],
      license_plate: ["license", "plate", "registration"],
      customer_name: ["name", "your name", "full name"],
      birth_date: ["birth", "born", "date of birth", "birthday", "dob"],
    };

    const fieldKeywords = keywords[field.name] || [field.name.replace(/_/g, " ")];
    if (fieldKeywords.some((kw) => msg.includes(kw))) {
      return field;
    }
  }

  // Default to first remaining field
  return remaining[0];
}

export function ChatWindow() {
  const { sessionId, messages, extractedFields, status, loading, error, send, reset } = useChat();
  const { schema } = useSchema();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, status]);

  const isCompleted = status === "completed";
  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");
  const currentField = detectCurrentField(
    schema?.fields,
    extractedFields,
    lastAssistantMsg?.content
  );

  // Show inline components only after the last message (not while loading, not after user just sent)
  const showInline = !loading && messages.length > 0 && messages[messages.length - 1]?.role === "assistant";

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--color-border-light)]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--color-rabo)] to-[#e65500] flex items-center justify-center shadow-sm">
            <svg viewBox="0 0 20 20" fill="white" className="w-4 h-4">
              <path fillRule="evenodd" d="M4.5 2A2.5 2.5 0 002 4.5v11A2.5 2.5 0 004.5 18h11a2.5 2.5 0 002.5-2.5v-11A2.5 2.5 0 0015.5 2h-11zM6 7a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h4a1 1 0 100-2H7z" clipRule="evenodd"/>
            </svg>
          </div>
          <div>
            <h1 className="text-[15px] font-semibold text-[var(--color-foreground)] leading-tight">
              {schema?.title || "Insurance Quote"}
            </h1>
            <SessionStatus status={status} />
          </div>
        </div>

        {/* Progress pills */}
        {schema && (
          <FieldProgress fields={schema.fields} extractedFields={extractedFields} />
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-2xl px-4 py-6">
          {/* Welcome state */}
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center py-16 animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--color-rabo-light)] to-white border border-[var(--color-border)] flex items-center justify-center mb-4">
                <svg viewBox="0 0 24 24" className="w-7 h-7 text-[var(--color-rabo)]" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"/>
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-1">
                {schema?.title || "Get Your Quote"}
              </h2>
              <p className="text-sm text-[var(--color-muted)] text-center max-w-sm mb-6">
                {schema?.description || "I'll collect a few details and prepare a personalized quote for you."}
              </p>
              <button
                onClick={() => send(`Hi, I'd like to get a ${schema?.title?.toLowerCase() || "quote"}`)}
                disabled={!sessionId}
                className="rounded-full border border-[var(--color-rabo)] bg-[var(--color-rabo-light)] px-5 py-2.5 text-sm font-medium text-[var(--color-rabo)] transition-all hover:bg-[var(--color-rabo)] hover:text-white active:scale-95 disabled:opacity-50"
              >
                Get Started
              </button>
            </div>
          )}

          {/* Message list */}
          <div className="space-y-4">
            {messages.map((msg, i) => (
              <MessageBubble
                key={i}
                message={msg}
                isLatest={i === messages.length - 1}
              />
            ))}

            {/* Loading indicator */}
            {loading && (
              <div className="flex gap-2.5 animate-fade-in">
                <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-[var(--color-rabo)] to-[#e65500] flex items-center justify-center">
                  <svg viewBox="0 0 16 16" className="w-3.5 h-3.5 text-white" fill="currentColor">
                    <path d="M8 1a7 7 0 100 14A7 7 0 008 1zM5.5 6.5a1 1 0 112 0 1 1 0 01-2 0zm3 0a1 1 0 112 0 1 1 0 01-2 0zM5.25 9.5a.5.5 0 01.7-.08A3.48 3.48 0 008 10.25c.78 0 1.5-.3 2.05-.83a.5.5 0 01.7.71A4.48 4.48 0 018 11.25a4.48 4.48 0 01-2.83-1.04.5.5 0 01-.08-.7h.16z"/>
                  </svg>
                </div>
                <div className="rounded-2xl rounded-bl-lg bg-[var(--color-surface)] border border-[var(--color-border)] px-4 py-3 shadow-sm">
                  <div className="flex gap-1.5">
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-[var(--color-muted-light)]"
                        style={{ animation: `pulse-dot 1.2s ease-in-out ${i * 0.2}s infinite` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Inline adaptive components — schema-driven, not hardcoded */}
            {showInline && currentField && !isCompleted && currentField.enum && (
              <QuickReplies
                options={currentField.enum}
                onSelect={send}
                disabled={loading}
              />
            )}

            {/* Confirm / Yes button when bot asks for confirmation */}
            {showInline && !currentField && !isCompleted && lastAssistantMsg && /confirm|correct|accurate/i.test(lastAssistantMsg.content) && (
              <QuickReplies
                options={["Yes, everything is correct", "No, I need to make changes"]}
                onSelect={send}
                disabled={loading}
              />
            )}

            {/* Summary card — only show when ALL fields are collected */}
            {showInline && schema && !isCompleted && !currentField && Object.keys(extractedFields).length >= schema.fields.length && (
              <SummaryCard fields={schema.fields} extractedFields={extractedFields} />
            )}

            {/* Completion celebration */}
            {isCompleted && <CompletionView onReset={reset} />}
          </div>

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-auto max-w-2xl px-4 pb-2 w-full">
          <div className="rounded-xl bg-red-50 border border-red-100 px-4 py-2.5 text-[13px] text-red-600">
            {error}
          </div>
        </div>
      )}

      {/* Input area */}
      {!isCompleted && (
        <div className="border-t border-[var(--color-border-light)] bg-[var(--color-background)]">
          <div className="mx-auto max-w-2xl px-4 py-3">
            <ChatInput
              onSend={send}
              disabled={loading || !sessionId}
              placeholder="Type a message..."
            />
          </div>
        </div>
      )}
    </div>
  );
}
