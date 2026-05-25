"use client";

import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api/client";
import type { ProfileSummary } from "@/lib/api/types";
import { useStudentId } from "@/lib/student";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

export default function ProfilePage() {
  const studentId = useStudentId();

  const { data, isLoading, error } = useQuery<ProfileSummary | null>({
    queryKey: ["profile", studentId],
    enabled: !!studentId,
    queryFn: async () => {
      if (!studentId) return null;
      try {
        return await api.getProfile(studentId);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });

  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col px-5 py-10 sm:py-16">
      <div className="mb-6 flex items-center justify-between">
        <Link
          href="/"
          className="text-sm text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
        >
          ← Home
        </Link>
        <UserButton />
      </div>

      {isLoading ? <Empty>Loading your profile…</Empty> : null}

      {error ? (
        <Empty>
          <span className="text-[var(--color-danger)]">
            Couldn&apos;t load your profile. Is the API running?
          </span>
        </Empty>
      ) : null}

      {!isLoading && !error && !data ? (
        <Empty>
          <p>You haven&apos;t started onboarding yet.</p>
          <Link href="/onboarding" className="mt-4 inline-block">
            <Button size="md">Begin</Button>
          </Link>
        </Empty>
      ) : null}

      {data ? <ProfileView profile={data} /> : null}
    </main>
  );
}

function ProfileView({ profile }: { profile: ProfileSummary }) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider text-[var(--color-fg-muted)]">
            Archetype
          </p>
          <h1 className="mt-1 text-2xl font-semibold capitalize">
            {profile.archetype.replace(/_/g, " ")}
          </h1>
        </div>
        <span className="rounded-full border border-[var(--color-border)] px-3 py-1 text-xs text-[var(--color-fg-muted)]">
          {profile.exam_target.toUpperCase().replace(/_/g, " ")}
        </span>
      </div>

      <div className="mt-6">
        <Progress
          value={profile.profile_confidence}
          label="Profile confidence"
        />
      </div>

      <dl className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Class level" value={titleCase(profile.class_level)} />
        <Field label="Language" value={profile.language.toUpperCase()} />
        <Field label="Weak subject" value={titleCase(profile.weak_subject)} />
        <Field label="Strong subject" value={titleCase(profile.strong_subject)} />
        <Field label="Main problem" value={profile.main_problem} />
        <Field label="Learning style" value={titleCase(profile.learning_style)} />
      </dl>

      {profile.missing_critical_fields.length > 0 ? (
        <div className="mt-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-4">
          <p className="text-sm">Still missing</p>
          <p className="mt-1 text-xs text-[var(--color-fg-muted)]">
            We need a few more answers before personalised chat opens.
          </p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {profile.missing_critical_fields.map((f) => (
              <li
                key={f}
                className="rounded-full border border-[var(--color-border)] px-2.5 py-1 text-xs capitalize text-[var(--color-fg-muted)]"
              >
                {f.replace(/_/g, " ")}
              </li>
            ))}
          </ul>
          <Link href="/onboarding" className="mt-4 inline-block">
            <Button size="sm" variant="outline">
              Continue onboarding
            </Button>
          </Link>
        </div>
      ) : (
        <div className="mt-8 flex flex-col gap-3 rounded-xl border border-[var(--color-success)]/30 bg-[var(--color-success)]/10 p-4 text-sm sm:flex-row sm:items-center sm:justify-between">
          <span>✓ Profile complete. You&apos;re ready to chat.</span>
          <Link href="/chat" className="inline-block">
            <Button size="sm">Open chat →</Button>
          </Link>
        </div>
      )}
    </Card>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-4 py-3">
      <dt className="text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)]">
        {label}
      </dt>
      <dd className="mt-1 text-sm">
        {value ? value : <span className="text-[var(--color-fg-muted)]">—</span>}
      </dd>
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <Card className="text-center">
      <div className="text-sm text-[var(--color-fg-muted)]">{children}</div>
    </Card>
  );
}

function titleCase(s: string | null | undefined): string | null {
  if (!s) return null;
  return s
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
