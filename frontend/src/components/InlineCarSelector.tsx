"use client";

const CAR_TYPES = [
  {
    value: "sedan",
    label: "Sedan",
    icon: (
      <svg viewBox="0 0 80 40" fill="none" className="w-full h-auto">
        <path d="M12 28h-4a2 2 0 01-2-2v-4l6-8h18l10 8v4a2 2 0 01-2 2h-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M24 14l-4-6h-6l-2 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        <path d="M24 14l6 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        <circle cx="16" cy="28" r="3" stroke="currentColor" strokeWidth="2"/>
        <circle cx="32" cy="28" r="3" stroke="currentColor" strokeWidth="2"/>
      </svg>
    ),
  },
  {
    value: "coupe",
    label: "Coupe",
    icon: (
      <svg viewBox="0 0 80 40" fill="none" className="w-full h-auto">
        <path d="M12 28h-4a2 2 0 01-2-2v-3l8-9h20l6 9v3a2 2 0 01-2 2h-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M22 14l-6-7h-2l-2 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        <path d="M22 14h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        <circle cx="16" cy="28" r="3" stroke="currentColor" strokeWidth="2"/>
        <circle cx="32" cy="28" r="3" stroke="currentColor" strokeWidth="2"/>
      </svg>
    ),
  },
  {
    value: "station wagon",
    label: "Station Wagon",
    icon: (
      <svg viewBox="0 0 80 40" fill="none" className="w-full h-auto">
        <path d="M12 28h-4a2 2 0 01-2-2v-6l6-8h24v8l2 6v2a2 2 0 01-2 2h-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M24 12l-4-6h-6l-2 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        <path d="M24 12h12v8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        <circle cx="16" cy="28" r="3" stroke="currentColor" strokeWidth="2"/>
        <circle cx="32" cy="28" r="3" stroke="currentColor" strokeWidth="2"/>
      </svg>
    ),
  },
  {
    value: "hatchback",
    label: "Hatchback",
    icon: (
      <svg viewBox="0 0 80 40" fill="none" className="w-full h-auto">
        <path d="M12 28h-4a2 2 0 01-2-2v-4l6-8h16l8 6v6a2 2 0 01-2 2h-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M22 14l-4-6h-4l-2 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        <path d="M22 14h6l4 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        <circle cx="16" cy="28" r="3" stroke="currentColor" strokeWidth="2"/>
        <circle cx="30" cy="28" r="3" stroke="currentColor" strokeWidth="2"/>
      </svg>
    ),
  },
  {
    value: "minivan",
    label: "Minivan",
    icon: (
      <svg viewBox="0 0 80 40" fill="none" className="w-full h-auto">
        <path d="M12 28h-4a2 2 0 01-2-2v-8l4-6h26v14a2 2 0 01-2 2h-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M18 12l-4-4h-4v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M18 12h18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        <path d="M24 12v10" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.4"/>
        <circle cx="16" cy="28" r="3" stroke="currentColor" strokeWidth="2"/>
        <circle cx="32" cy="28" r="3" stroke="currentColor" strokeWidth="2"/>
      </svg>
    ),
  },
];

interface Props {
  onSelect: (value: string) => void;
  disabled?: boolean;
}

export function InlineCarSelector({ onSelect, disabled }: Props) {
  return (
    <div className="animate-scale-in pl-10 pt-2 pb-2">
      <div className="grid grid-cols-3 gap-2 max-w-md sm:grid-cols-5">
        {CAR_TYPES.map((car, i) => (
          <button
            key={car.value}
            onClick={() => !disabled && onSelect(car.value)}
            disabled={disabled}
            className="group flex flex-col items-center gap-1.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 transition-all duration-200 hover:border-[var(--color-rabo)] hover:bg-[var(--color-rabo-light)] hover:shadow-sm active:scale-95 disabled:opacity-40 disabled:pointer-events-none animate-fade-in-up"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <div className="w-12 h-8 text-[var(--color-muted)] group-hover:text-[var(--color-rabo)] transition-colors">
              {car.icon}
            </div>
            <span className="text-[11px] font-medium text-[var(--color-muted)] group-hover:text-[var(--color-rabo)] transition-colors leading-tight text-center">
              {car.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
