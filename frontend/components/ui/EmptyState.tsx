import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon,
  title,
  description,
  className,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-outline-variant bg-surface-bright px-6 py-14 text-center",
        className
      )}
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-surface-container-lowest shadow-sm ring-1 ring-outline-variant">
        <Icon className="h-5 w-5 text-outline" />
      </div>
      <p className="text-body-sm font-medium text-on-surface">{title}</p>
      {description && <p className="text-body-sm text-text-muted">{description}</p>}
    </div>
  );
}
