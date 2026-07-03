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
          "h-10 w-full rounded border border-outline-variant bg-surface-container-lowest px-3 text-body-sm text-on-surface placeholder:text-text-muted transition-shadow focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary-container",
          className
        )}
        {...props}
      />
    );

    if (!label) return inputEl;

    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={id} className="font-label text-label-caps text-on-surface-variant">
          {label}
        </label>
        {inputEl}
      </div>
    );
  }
);
Input.displayName = "Input";

export { Input };
