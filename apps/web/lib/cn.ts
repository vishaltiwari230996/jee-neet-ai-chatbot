import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Conditional + de-duplicated Tailwind class joiner.
 * Used by every UI primitive so we never get duplicate utility classes
 * fighting each other.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
