"use client";

import type { TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface TextInputProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export function TextInput({ label, className, ...rest }: TextInputProps) {
  return (
    <label className="flex w-full flex-col gap-2">
      {label ? (
        <span className="text-xs text-[var(--color-fg-muted)]">{label}</span>
      ) : null}
      <textarea
        className={cn(
          "min-h-[88px] w-full resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-4 py-3 text-[15px] placeholder:text-[var(--color-fg-muted)] focus-ring",
          className,
        )}
        {...rest}
      />
    </label>
  );
}
