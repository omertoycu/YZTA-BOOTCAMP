import { Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-600 to-brand-400 text-white shadow-sm">
        <Building2 className="h-[18px] w-[18px]" strokeWidth={2.25} />
      </span>
      <span className="text-base font-semibold tracking-tight text-slate-900">PortföyAI</span>
    </div>
  );
}
