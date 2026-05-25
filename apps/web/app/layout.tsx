import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { QueryProvider } from "./query-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "NeetAI — Personalized JEE/NEET tutor",
  description:
    "An AI tutor that learns how you study, then explains the way that works for you.",
};

export const viewport: Viewport = {
  themeColor: "#0b0d10",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-dvh">
        <ClerkProvider
          appearance={{
            variables: {
              colorPrimary: "#7c9cff",
              colorBackground: "#11141a",
              colorInputBackground: "#0b0d10",
              colorText: "#e6e8eb",
              colorTextSecondary: "#9aa4b2",
              colorInputText: "#e6e8eb",
              colorNeutral: "#ffffff",
              borderRadius: "0.75rem",
            },
            elements: {
              card: "bg-[var(--color-bg-elevated)] border border-[var(--color-border)] shadow-none",
              headerTitle: "text-[var(--color-fg)]",
              headerSubtitle: "text-[var(--color-fg-muted)]",
            },
          }}
        >
          <QueryProvider>{children}</QueryProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
