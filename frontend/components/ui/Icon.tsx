import { cn } from "@/lib/utils";

export function Icon({
  name,
  filled = false,
  className,
}: {
  name: string;
  filled?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn("material-symbols-outlined select-none", filled && "icon-fill", className)}
      aria-hidden="true"
    >
      {name}
    </span>
  );
}
