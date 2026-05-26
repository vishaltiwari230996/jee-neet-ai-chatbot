"use client";

import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col px-6 py-8 sm:py-10">
      {/* Top nav: auth controls live here so they're always reachable */}
      <nav className="mb-12 flex items-center justify-between">
        <BrandSwitcher />
        <div className="flex items-center gap-2">
          <Link
            href="/chat"
            className="text-sm text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
          >
            Chat
          </Link>
          <Link
            href="/profile"
            className="text-sm text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
          >
            Profile
          </Link>
          <Link
            href="/sign-in"
            className="text-sm text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
          >
            Sign in
          </Link>
          <Link
            href="/sign-up"
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-3 py-1.5 text-sm hover:border-[var(--color-brand)]"
          >
            Sign up
          </Link>
          <UserButton />
        </div>
      </nav>

      <div className="flex flex-1 flex-col justify-center">
        <div className="mb-2 inline-flex w-fit items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-3 py-1 text-xs text-[var(--color-fg-muted)]">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-success)]" />
          Personalised for your way of learning
        </div>

        <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">
          An AI tutor that{" "}
          <span className="text-[var(--color-brand)]">studies you</span>, not
          just the syllabus.
        </h1>

        <p className="mt-5 max-w-xl text-[15px] leading-7 text-[var(--color-fg-muted)]">
          Three minutes of questions are all it takes. NeetAI builds a profile
          of where you&apos;re strong, where you struggle, and how you actually
          understand things — then explains every doubt the way that works for
          you.
        </p>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link href="/chat">
            <Button size="lg" className="w-full sm:w-auto">
              Open chat
            </Button>
          </Link>
          <Link href="/onboarding">
            <Button size="lg" variant="outline" className="w-full sm:w-auto">
              Continue onboarding
            </Button>
          </Link>
          <Link href="/sign-up">
            <Button size="lg" variant="ghost" className="w-full sm:w-auto">
              Sign up
            </Button>
          </Link>
        </div>

        <ul className="mt-12 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {[
            ["Diagnostic", "10 short questions"],
            ["Personalised", "Tuned to your archetype"],
            ["Honest", "Confidence shown on every answer"],
          ].map(([title, body]) => (
            <li
              key={title}
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-4 py-3"
            >
              <p className="text-sm font-medium">{title}</p>
              <p className="mt-0.5 text-xs text-[var(--color-fg-muted)]">
                {body}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}

function BrandSwitcher() {
  return (
    <span
      className="brand-switcher"
      aria-label="JEE AI and NEET AI"
      role="img"
    >
      <span className="brand-switcher__item brand-switcher__item--jee">
        JEE AI
      </span>
      <span className="brand-switcher__item brand-switcher__item--neet">
        NEET AI
      </span>
    </span>
  );
}
