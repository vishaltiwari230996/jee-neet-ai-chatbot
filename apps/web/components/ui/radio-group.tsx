"use client";

import { cn } from "@/lib/cn";

interface RadioGroupProps {
  name: string;
  options: readonly string[];
  value: string | null;
  onChange: (value: string) => void;
  disabled?: boolean;
}

/**
 * Native-radio-backed group styled as a vertical stack of touchable cards.
 * Mobile-first: each option is a full-width tap target ≥ 56px tall.
 */
export function RadioGroup({
  name,
  options,
  value,
  onChange,
  disabled = false,
}: RadioGroupProps) {
  return (
    <div className="flex flex-col gap-2" role="radiogroup">
      {options.map((option) => {
        const selected = value === option;
        return (
          <label
            key={option}
            className={cn(
              "flex min-h-14 cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 text-[15px] transition-colors focus-ring",
              selected
                ? "border-[var(--color-brand)] bg-[var(--color-brand)]/10"
                : "border-[var(--color-border)] bg-[var(--color-bg-elevated)] hover:border-[var(--color-fg-muted)]",
              disabled && "cursor-not-allowed opacity-60",
            )}
          >
            <input
              type="radio"
              name={name}
              value={option}
              checked={selected}
              onChange={() => onChange(option)}
              disabled={disabled}
              className="sr-only"
            />
            <span
              aria-hidden
              className={cn(
                "flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                selected
                  ? "border-[var(--color-brand)] bg-[var(--color-brand)]"
                  : "border-[var(--color-border)]",
              )}
            >
              {selected ? <span className="h-2 w-2 rounded-full bg-white" /> : null}
            </span>
            <span className="capitalize">{option.replace(/_/g, " ")}</span>
          </label>
        );
      })}
    </div>
  );
}
