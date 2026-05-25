import { cn } from "@/lib/cn";

interface ProgressProps {
  /** A value between 0 and 1. */
  value: number;
  className?: string;
  label?: string;
}

export function Progress({ value, className, label }: ProgressProps) {
  const clamped = Math.max(0, Math.min(1, value));
  const pct = Math.round(clamped * 100);
  return (
    <div className={cn("w-full", className)}>
      {label ? (
        <div className="mb-2 flex items-center justify-between text-xs text-[var(--color-fg-muted)]">
          <span>{label}</span>
          <span>{pct}%</span>
        </div>
      ) : null}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--color-border)]">
        <div
          className="h-full rounded-full bg-[var(--color-brand)] transition-[width] duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
