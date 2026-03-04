"use client";

interface Props {
  options: string[];
  onSelect: (value: string) => void;
  disabled?: boolean;
}

export function QuickReplies({ options, onSelect, disabled }: Props) {
  return (
    <div className="animate-fade-in-up flex flex-wrap gap-2 pl-10 pt-1 pb-2">
      {options.map((option, i) => (
        <button
          key={option}
          onClick={() => !disabled && onSelect(option)}
          disabled={disabled}
          className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2 text-[13px] font-medium text-[var(--color-foreground)] transition-all duration-200 hover:border-[var(--color-rabo)] hover:bg-[var(--color-rabo-light)] hover:text-[var(--color-rabo)] active:scale-95 disabled:opacity-40 disabled:pointer-events-none"
          style={{ animationDelay: `${i * 50}ms` }}
        >
          {option}
        </button>
      ))}
    </div>
  );
}
