"use client";

import { useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Stats {
  sessions: { total: number; active: number; completed: number };
  registrations: number;
}

export default function AdminPage() {
  const [tab, setTab] = useState<"sessions" | "registrations">("sessions");
  const [stats, setStats] = useState<Stats | null>(null);
  const [sessions, setSessions] = useState<Record<string, unknown>[]>([]);
  const [registrations, setRegistrations] = useState<Record<string, unknown>[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [statsRes, sessionsRes, regsRes] = await Promise.all([
      fetch(`${API}/api/admin/stats`).then((r) => r.json()),
      fetch(`${API}/api/admin/sessions?limit=100`).then((r) => r.json()),
      fetch(`${API}/api/admin/registrations?limit=100`).then((r) => r.json()),
    ]);
    setStats(statsRes);
    setSessions(sessionsRes.sessions);
    setRegistrations(regsRes.registrations);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const clearSessions = async () => {
    await fetch(`${API}/api/admin/sessions`, { method: "DELETE" });
    refresh();
  };

  const clearRegistrations = async () => {
    await fetch(`${API}/api/admin/registrations`, { method: "DELETE" });
    refresh();
  };

  return (
    <div className="min-h-screen bg-[var(--color-background)]">
      {/* Header */}
      <div className="border-b border-[var(--color-border-light)] bg-[var(--color-surface)]">
        <div className="mx-auto max-w-5xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <a href="/" className="text-[var(--color-muted)] hover:text-[var(--color-foreground)] transition-colors">
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path fillRule="evenodd" d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z" clipRule="evenodd"/>
              </svg>
            </a>
            <h1 className="text-[16px] font-semibold text-[var(--color-foreground)]">Admin Panel</h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={refresh}
              className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-[12px] font-medium text-[var(--color-muted)] hover:text-[var(--color-foreground)] hover:border-[var(--color-foreground)] transition-all"
            >
              Refresh
            </button>
            <button
              onClick={clearSessions}
              className="rounded-lg border border-red-200 px-3 py-1.5 text-[12px] font-medium text-red-500 hover:bg-red-50 transition-all"
            >
              Clear Sessions
            </button>
            <button
              onClick={clearRegistrations}
              className="rounded-lg border border-red-200 px-3 py-1.5 text-[12px] font-medium text-red-500 hover:bg-red-50 transition-all"
            >
              Clear Registrations
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-6 py-6">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-4 gap-3 mb-6">
            {[
              { label: "Total Sessions", value: stats.sessions.total, color: "var(--color-foreground)" },
              { label: "Active", value: stats.sessions.active, color: "#22c55e" },
              { label: "Completed", value: stats.sessions.completed, color: "#3b82f6" },
              { label: "Registrations", value: stats.registrations, color: "var(--color-rabo)" },
            ].map((stat) => (
              <div key={stat.label} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
                <p className="text-[11px] font-medium text-[var(--color-muted)] uppercase tracking-wider mb-1">{stat.label}</p>
                <p className="text-2xl font-semibold" style={{ color: stat.color }}>{stat.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-[var(--color-border-light)]">
          {(["sessions", "registrations"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-[13px] font-medium border-b-2 transition-colors -mb-px ${
                tab === t
                  ? "border-[var(--color-rabo)] text-[var(--color-rabo)]"
                  : "border-transparent text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
              }`}
            >
              {t === "sessions" ? `Sessions (${sessions.length})` : `Registrations (${registrations.length})`}
            </button>
          ))}
        </div>

        {/* Sessions Table */}
        {tab === "sessions" && (
          <div className="space-y-2">
            {sessions.length === 0 && (
              <p className="text-sm text-[var(--color-muted)] py-8 text-center">No sessions found.</p>
            )}
            {sessions.map((s) => {
              const id = String(s.session_id);
              const isExpanded = expanded === id;
              const fields = (s.extracted_fields || {}) as Record<string, unknown>;
              const messages = (s.messages || []) as { role: string; content: string }[];
              const fieldCount = Object.keys(fields).length;

              return (
                <div key={id} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
                  <button
                    onClick={() => setExpanded(isExpanded ? null : id)}
                    className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[var(--color-background)] transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="font-mono text-[12px] text-[var(--color-muted)]">{id.slice(0, 8)}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        s.status === "completed" ? "bg-blue-50 text-blue-600" :
                        s.status === "active" ? "bg-green-50 text-green-600" :
                        s.status === "duplicate_detected" ? "bg-orange-50 text-orange-600" :
                        "bg-gray-100 text-gray-500"
                      }`}>
                        {String(s.status)}
                      </span>
                      {fieldCount > 0 && (
                        <span className="text-[12px] text-[var(--color-muted)]">{fieldCount} fields</span>
                      )}
                      {typeof s.schema_version === "string" && (
                        <span className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-muted-light)]">
                          {s.schema_version.slice(0, 8)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-[var(--color-muted-light)]">{messages.length} msgs</span>
                      <svg className={`w-4 h-4 text-[var(--color-muted-light)] transition-transform ${isExpanded ? "rotate-180" : ""}`} viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd"/>
                      </svg>
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="border-t border-[var(--color-border-light)] px-4 py-3 space-y-3">
                      {/* Extracted fields */}
                      {fieldCount > 0 && (
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-muted)] mb-2">Extracted Fields</p>
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                            {Object.entries(fields).map(([k, v]) => (
                              <div key={k} className="flex justify-between gap-2">
                                <span className="text-[12px] text-[var(--color-muted)]">{k}</span>
                                <span className="text-[12px] font-medium text-[var(--color-foreground)] truncate">{String(v)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Messages */}
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-muted)] mb-2">Conversation</p>
                        <div className="space-y-1.5 max-h-64 overflow-y-auto">
                          {messages.map((m, i) => (
                            <div key={i} className={`text-[12px] leading-relaxed ${m.role === "user" ? "text-[var(--color-foreground)]" : "text-[var(--color-muted)]"}`}>
                              <span className="font-semibold">{m.role === "user" ? "User" : "Bot"}:</span>{" "}
                              {m.content || "(empty)"}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Registrations Table */}
        {tab === "registrations" && (
          <div className="space-y-2">
            {registrations.length === 0 && (
              <p className="text-sm text-[var(--color-muted)] py-8 text-center">No registrations yet. Complete a conversation to see data here.</p>
            )}
            {registrations.map((r, i) => {
              const fields = (r.fields || {}) as Record<string, unknown>;
              const history = (r.history || []) as Record<string, unknown>[];

              return (
                <div key={i} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 bg-[var(--color-background)] border-b border-[var(--color-border-light)]">
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-[var(--color-rabo-light)] px-2 py-0.5 text-[11px] font-medium text-[var(--color-rabo)]">
                        Registration
                      </span>
                      <span className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-muted)]">
                        prompt: {String(r.schema_version).slice(0, 8)}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      {history.length > 0 && (
                        <span className="text-[11px] text-[var(--color-muted)]">{history.length} update(s)</span>
                      )}
                      <span className="text-[11px] text-[var(--color-muted-light)]">
                        PII: {String(r.pii_hash).slice(0, 12)}...
                      </span>
                    </div>
                  </div>

                  <div className="px-4 py-3 grid grid-cols-2 gap-x-6 gap-y-2">
                    {Object.entries(fields).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-2">
                        <span className="text-[12px] text-[var(--color-muted)]">{k}</span>
                        <span className="text-[12px] font-medium text-[var(--color-foreground)]">{String(v)}</span>
                      </div>
                    ))}
                  </div>

                  {history.length > 0 && (
                    <div className="px-4 py-3 border-t border-[var(--color-border-light)]">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-muted)] mb-2">Previous Versions</p>
                      <div className="space-y-2">
                        {history.map((h, hi) => (
                          <div key={hi} className="rounded-lg bg-[var(--color-background)] p-2.5">
                            <div className="flex items-center gap-2 mb-1.5">
                              <span className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-muted-light)]">
                                prompt: {String(h.schema_version || "unknown").slice(0, 8)}
                              </span>
                              <span className="text-[10px] text-[var(--color-muted-light)]">
                                {String(h.archived_at || "").slice(0, 10)}
                              </span>
                            </div>
                            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                              {Object.entries((h.fields || {}) as Record<string, unknown>).map(([k, v]) => (
                                <div key={k} className="flex justify-between gap-2">
                                  <span className="text-[11px] text-[var(--color-muted-light)]">{k}</span>
                                  <span className="text-[11px] text-[var(--color-muted)]">{String(v)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
