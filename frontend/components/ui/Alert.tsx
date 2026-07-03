import { AlertCircle } from "lucide-react";
import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Alert({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded border border-error-container bg-error-container px-3.5 py-2.5 text-body-sm text-on-error-container",
        className
      )}
    >
      <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
      <span>{children}</span>
    </div>
  );
}
