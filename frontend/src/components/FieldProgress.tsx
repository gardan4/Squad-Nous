"use client";

import type { FieldInfo } from "@/lib/types";

const SHORT_LABELS: Record<string, string> = {
  car_type: "Type",
  manufacturer: "Make",
  year_of_construction: "Year",
  license_plate: "Plate",
  customer_name: "Name",
  birth_date: "DOB",
};

interface Props {
  fields: FieldInfo[];
  extractedFields: Record<string, unknown>;
}

export function FieldProgress({ fields, extractedFields }: Props) {
  const completedCount = fields.filter(
    (f) => extractedFields[f.name] !== undefined && extractedFields[f.name] !== ""
  ).length;

  const percentage = fields.length > 0 ? (completedCount / fields.length) * 100 : 0;

  return (
    <div className="flex items-center gap-3 min-w-0">
      {/* Progress bar */}
      <div className="hidden sm:flex items-center gap-1.5 min-w-0">
        {fields.map((field) => {
          const done = extractedFields[field.name] !== undefined && extractedFields[field.name] !== "";
          return (
            <div key={field.name} className="flex items-center gap-1.5">
              <div
                className={`h-1.5 w-6 rounded-full transition-all duration-500 ${
                  done ? "bg-[var(--color-rabo)]" : "bg-[var(--color-border)]"
                }`}
              />
            </div>
          );
        })}
      </div>

      {/* Mobile: simple fraction */}
      <span className="text-[12px] font-medium text-[var(--color-muted)] tabular-nums whitespace-nowrap">
        {completedCount}/{fields.length}
      </span>
    </div>
  );
}
