"use client";

import type { PropertyType } from "@/lib/types";
import { cn } from "@/lib/utils";

const PROPERTY_TYPE_LABELS: Record<PropertyType, string> = {
  residential: "Konut",
  commercial: "İş Yeri",
  land: "Arsa",
};

export function PropertyTypeSelect({
  value,
  onChange,
  className,
}: {
  value: PropertyType;
  onChange: (value: PropertyType) => void;
  className?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as PropertyType)}
      aria-label="Emlak tipi"
      className={cn(
        "h-10 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 text-body-sm text-on-surface focus:border-secondary focus:outline-none",
        className
      )}
    >
      {(Object.entries(PROPERTY_TYPE_LABELS) as [PropertyType, string][]).map(([type, label]) => (
        <option key={type} value={type}>
          {label}
        </option>
      ))}
    </select>
  );
}
