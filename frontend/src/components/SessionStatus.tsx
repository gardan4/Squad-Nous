"use client";

interface Props {
  status: string;
}

export function SessionStatus({ status }: Props) {
  const isActive = status === "active" || status === "duplicate_detected";
  const isCompleted = status === "completed";

  return (
    <div className="flex items-center gap-1.5">
      <div
        className={`w-1.5 h-1.5 rounded-full ${
          isCompleted
            ? "bg-blue-500"
            : isActive
              ? "bg-emerald-500 animate-pulse"
              : "bg-[var(--color-muted-light)]"
        }`}
      />
      <span className="text-[11px] font-medium text-[var(--color-muted)]">
        {isCompleted ? "Completed" : isActive ? "Online" : "Connecting"}
      </span>
    </div>
  );
}
