"use client";

interface Props {
  onReset: () => void;
}

export function CompletionView({ onReset }: Props) {
  return (
    <div className="animate-scale-in flex flex-col items-center py-8 px-4">
      {/* Animated checkmark */}
      <div className="relative mb-6">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center shadow-lg shadow-green-200">
          <svg viewBox="0 0 24 24" className="w-10 h-10 text-white" fill="none">
            <path
              d="M5 13l4 4L19 7"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="24"
              strokeDashoffset="24"
              style={{ animation: "checkmark-draw 0.4s ease-out 0.3s forwards" }}
            />
          </svg>
        </div>
        {/* Confetti particles */}
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 rounded-full"
            style={{
              background: ["#ff6600", "#fbbf24", "#34d399", "#60a5fa", "#a78bfa", "#f472b6", "#ff6600", "#34d399"][i],
              top: "50%",
              left: "50%",
              animation: `confetti-fall 1s ease-out ${0.2 + i * 0.08}s forwards`,
              transform: `rotate(${i * 45}deg) translateX(${30 + (i % 3) * 10}px)`,
              opacity: 0,
            }}
          />
        ))}
      </div>

      <h3 className="text-xl font-semibold text-[var(--color-foreground)] mb-1">
        Quote Submitted
      </h3>
      <p className="text-sm text-[var(--color-muted)] mb-6 text-center max-w-xs">
        Your car insurance quote request has been registered. Our team will get back to you shortly.
      </p>

      <button
        onClick={onReset}
        className="rounded-full bg-[var(--color-foreground)] px-6 py-2.5 text-sm font-medium text-white transition-all hover:opacity-80 active:scale-95"
      >
        Start New Quote
      </button>
    </div>
  );
}
