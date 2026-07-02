import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, id, ...props }, ref) => {
    const inputEl = (
      <input
        ref={ref}
        id={id}
        className={cn(
          "h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 transition-shadow focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100",
          className
        )}
        {...props}
      />
    );

    if (!label) return inputEl;

    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={id} className="text-xs font-medium text-slate-600">
          {label}
        </label>
        {inputEl}
      </div>
    );
  }
);
Input.displayName = "Input";

export { Input };
