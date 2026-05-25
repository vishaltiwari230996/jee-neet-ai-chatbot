import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function Card({ className, children, ...rest }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-6 shadow-[0_1px_0_rgba(255,255,255,0.03)_inset]",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
