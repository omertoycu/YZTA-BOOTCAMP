"use client";

import type { ListingType } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ListingTypeToggle({
  value,
  onChange,
  className,
}: {
  value: ListingType;
  onChange: (value: ListingType) => void;
  className?: string;
}) {
  return (
    <div className={cn("inline-flex w-fit rounded-full bg-surface-container p-1", className)}>
      {(["sale", "rent"] as const).map((type) => (
        <button
          key={type}
          type="button"
          onClick={() => onChange(type)}
          className={cn(
            "rounded-full px-4 py-1.5 text-body-sm font-medium transition-colors",
            value === type ? "bg-primary text-on-primary shadow-sm" : "text-text-muted hover:text-primary"
          )}
        >
          {type === "sale" ? "Satılık" : "Kiralık"}
        </button>
      ))}
    </div>
  );
}
