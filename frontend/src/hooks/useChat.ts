"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createSession, sendMessage } from "@/lib/api";
import type { ChatResponse, Message } from "@/lib/types";

export function useChat() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [extractedFields, setExtractedFields] = useState<
    Record<string, unknown>
  >({});
  const [status, setStatus] = useState<string>("idle");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initRef = useRef(false);

  // Create session on mount
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    createSession()
      .then((res) => {
        setSessionId(res.session_id);
        setStatus("active");
      })
      .catch((e) => setError(e.message));
  }, []);

  const send = useCallback(
    async (content: string) => {
      if (!sessionId || loading) return;

      setLoading(true);
      setError(null);

      // Add user message optimistically
      const userMsg: Message = { role: "user", content };
      setMessages((prev) => [...prev, userMsg]);

      try {
        const res: ChatResponse = await sendMessage(sessionId, content);

        const assistantMsg: Message = { role: "assistant", content: res.response };
        setMessages((prev) => [...prev, assistantMsg]);
        setExtractedFields(res.extracted_fields);
        setStatus(res.status);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to send message");
      } finally {
        setLoading(false);
      }
    },
    [sessionId, loading]
  );

  const reset = useCallback(async () => {
    setMessages([]);
    setExtractedFields({});
    setStatus("idle");
    setError(null);
    initRef.current = false;

    try {
      const res = await createSession();
      setSessionId(res.session_id);
      setStatus("active");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create session");
    }
  }, []);

  return {
    sessionId,
    messages,
    extractedFields,
    status,
    loading,
    error,
    send,
    reset,
  };
}
