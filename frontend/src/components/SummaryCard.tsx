"use client";

import type { FieldInfo } from "@/lib/types";

const FIELD_LABELS: Record<string, string> = {
  car_type: "Car Type",
  manufacturer: "Manufacturer",
  year_of_construction: "Year",
  license_plate: "License Plate",
  customer_name: "Name",
  birth_date: "Date of Birth",
};

interface Props {
  fields: FieldInfo[];
  extractedFields: Record<string, unknown>;
}

export function SummaryCard({ fields, extractedFields }: Props) {
  const filledFields = fields.filter(
    (f) => extractedFields[f.name] !== undefined && extractedFields[f.name] !== ""
  );

  if (filledFields.length < 2) return null;

  return (
    <div className="animate-scale-in pl-10 pt-2 pb-2">
      <div className="max-w-sm rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden shadow-sm">
        <div className="px-4 py-3 bg-gradient-to-r from-[var(--color-rabo-light)] to-transparent border-b border-[var(--color-border-light)]">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-rabo)]">
            Quote Summary
          </p>
        </div>
        <div className="px-4 py-3 space-y-2.5">
          {filledFields.map((field, i) => (
            <div
              key={field.name}
              className="flex items-center justify-between gap-3 animate-fade-in"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <span className="text-[12px] text-[var(--color-muted)]">
                {FIELD_LABELS[field.name] || field.description}
              </span>
              <span className="text-[13px] font-medium text-[var(--color-foreground)] text-right truncate max-w-[180px]">
                {String(extractedFields[field.name])}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
