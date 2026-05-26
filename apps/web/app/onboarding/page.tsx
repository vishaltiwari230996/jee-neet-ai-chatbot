"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api/client";
import type {
  ClassLevel,
  ExamTarget,
  OnboardingStateResponse,
  QuestionPayload,
} from "@/lib/api/types";
import { useStudentId } from "@/lib/student";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { RadioGroup } from "@/components/ui/radio-group";
import { TextInput } from "@/components/ui/text-input";

/**
 * The onboarding flow has three steps:
 *
 *  1. `intake`   — pick class level + exam target. Required by the API to
 *                  start the flow. One screen.
 *  2. `questions`— the adaptive diagnostic loop. Each iteration shows the
 *                  question the API just sent back; submitting an answer
 *                  returns the next state.
 *  3. `complete` — the API has no more questions; we route to /profile.
 *
 * Everything is driven by `OnboardingStateResponse` from the server, so
 * refreshing the page mid-flow Just Works (we re-fetch `/state/{id}`).
 */
type Phase = "intake" | "questions" | "complete";

const CLASS_LEVELS: ClassLevel[] = ["class_11", "class_12", "dropper"];
const EXAM_TARGETS: ExamTarget[] = [
  "jee_main",
  "jee_advanced",
  "neet",
  "jee_main_advanced",
];

const EXPECTED_ONBOARDING_QUESTIONS = 9;

export default function OnboardingPage() {
  const queryClient = useQueryClient();
  // Identity comes from Clerk if signed in, otherwise a localStorage fallback,
  // so the page never blocks on third-party auth state.
  const studentId = useStudentId();
  const [classLevel, setClassLevel] = useState<ClassLevel | null>(null);
  const [examTarget, setExamTarget] = useState<ExamTarget | null>(null);

  // If a previous run already started, resume it without forcing the user
  // back to the intake screen.
  const existing = useQuery<OnboardingStateResponse | null>({
    queryKey: ["onboarding", studentId, "resume"],
    enabled: !!studentId,
    queryFn: async () => {
      if (!studentId) return null;
      try {
        return await api.getOnboardingState(studentId);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });

  const startMutation = useMutation({
    mutationFn: api.startOnboarding,
    onSuccess: (data) => {
      queryClient.setQueryData(["onboarding", studentId, "resume"], data);
    },
  });

  const answerMutation = useMutation({
    mutationFn: api.submitAnswer,
    onSuccess: (data) => {
      queryClient.setQueryData(["onboarding", studentId, "resume"], data);
    },
  });

  if (!studentId) {
    return <CenterMessage>Preparing your session…</CenterMessage>;
  }

  if (existing.isLoading) {
    return <CenterMessage>Loading your profile…</CenterMessage>;
  }

  if (existing.isError) {
    return (
      <CenterMessage>
        <p className="text-[var(--color-danger)]">
          Couldn&apos;t reach the API. Is the backend running on port 8000?
        </p>
      </CenterMessage>
    );
  }

  const state: OnboardingStateResponse | null = existing.data ?? null;
  const mutationError = (startMutation.error ?? answerMutation.error) as
    | Error
    | null;

  const phase: Phase = !state
    ? "intake"
    : state.status === "complete"
      ? "complete"
      : "questions";

  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col px-5 py-10 sm:py-16">
      <Header />

      {phase === "intake" ? (
        <IntakeStep
          classLevel={classLevel}
          examTarget={examTarget}
          onClassLevel={setClassLevel}
          onExamTarget={setExamTarget}
          submitting={startMutation.isPending}
          onSubmit={() => {
            if (!classLevel || !examTarget || !studentId) return;
            startMutation.mutate({
              student_id: studentId,
              class_level: classLevel,
              exam_target: examTarget,
            });
          }}
        />
      ) : null}

      {phase === "questions" && state ? (
        <QuestionStep
          state={state}
          submitting={answerMutation.isPending}
          onAnswer={(answer) => {
            if (!state.next_question || !studentId) return;
            answerMutation.mutate({
              student_id: studentId,
              question_id: state.next_question.question_id,
              raw_answer: answer,
            });
          }}
        />
      ) : null}

      {phase === "complete" ? <CompleteStep /> : null}

      {mutationError ? (
        <p className="mt-4 text-sm text-[var(--color-danger)]">
          {mutationError instanceof ApiError
            ? mutationError.message
            : "Something went wrong. Try again."}
        </p>
      ) : null}
    </main>
  );
}

/* -------------------------------------------------------------------------- */

function Header() {
  return (
    <div className="mb-6 flex items-center justify-between">
      <Link
        href="/"
        className="text-sm text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
      >
        ← Back
      </Link>
      <UserButton />
    </div>
  );
}

function IntakeStep({
  classLevel,
  examTarget,
  onClassLevel,
  onExamTarget,
  submitting,
  onSubmit,
}: {
  classLevel: ClassLevel | null;
  examTarget: ExamTarget | null;
  onClassLevel: (v: ClassLevel) => void;
  onExamTarget: (v: ExamTarget) => void;
  submitting: boolean;
  onSubmit: () => void;
}) {
  const ready = classLevel !== null && examTarget !== null;
  return (
    <Card>
      <h1 className="text-xl font-semibold">Let&apos;s get to know you</h1>
      <p className="mt-1 text-sm text-[var(--color-fg-muted)]">
        Two quick picks and we&apos;ll start.
      </p>

      <div className="mt-6 space-y-6">
        <FieldGroup label="Where are you in school?">
          <RadioGroup
            name="class_level"
            options={CLASS_LEVELS}
            value={classLevel}
            onChange={(v) => onClassLevel(v as ClassLevel)}
          />
        </FieldGroup>

        <FieldGroup label="Which exam are you targeting?">
          <RadioGroup
            name="exam_target"
            options={EXAM_TARGETS}
            value={examTarget}
            onChange={(v) => onExamTarget(v as ExamTarget)}
          />
        </FieldGroup>
      </div>

      <div className="mt-8">
        <Button
          size="lg"
          className="w-full"
          disabled={!ready || submitting}
          onClick={onSubmit}
        >
          {submitting ? "Starting…" : "Continue"}
        </Button>
      </div>
    </Card>
  );
}

function QuestionStep({
  state,
  submitting,
  onAnswer,
}: {
  state: OnboardingStateResponse;
  submitting: boolean;
  onAnswer: (raw: string) => void;
}) {
  const q = state.next_question;
  if (!q) return null;

  // The backend raises profile confidence by 0.10 per diagnostic answer.
  // The current CSV has nine post-intake questions, so this gives students
  // a stable progress bar without exposing internal field names.
  const answered = Math.min(
    EXPECTED_ONBOARDING_QUESTIONS,
    Math.round(state.profile.profile_confidence * 10),
  );
  const progress = Math.min(1, answered / EXPECTED_ONBOARDING_QUESTIONS);

  return (
    <Card>
      <Progress
        value={progress}
        label={`Step ${Math.min(answered + 1, EXPECTED_ONBOARDING_QUESTIONS)} of ${EXPECTED_ONBOARDING_QUESTIONS}`}
      />

      <h2 className="mt-6 text-[17px] font-medium leading-7">{q.text}</h2>
      <p className="mt-1 text-xs uppercase tracking-wider text-[var(--color-fg-muted)]">
        {q.category.replace(/_/g, " ")}
      </p>

      <div className="mt-6">
        <AnswerInput question={q} submitting={submitting} onSubmit={onAnswer} />
      </div>
    </Card>
  );
}

function AnswerInput({
  question,
  submitting,
  onSubmit,
}: {
  question: QuestionPayload;
  submitting: boolean;
  onSubmit: (raw: string) => void;
}) {
  const [choice, setChoice] = useState<string | null>(null);
  const [text, setText] = useState("");

  // Reset local state whenever the question changes — otherwise the
  // previous answer leaks into the next screen.
  useEffect(() => {
    setChoice(null);
    setText("");
  }, [question.question_id]);

  const isChoice = question.options.length > 0;
  const canSubmit = isChoice ? choice !== null : text.trim().length > 0;

  return (
    <div className="space-y-5">
      {isChoice ? (
        <RadioGroup
          name={question.question_id}
          options={question.options}
          value={choice}
          onChange={setChoice}
          disabled={submitting}
        />
      ) : (
        <TextInput
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type your answer…"
          disabled={submitting}
        />
      )}

      <Button
        size="lg"
        className="w-full"
        disabled={!canSubmit || submitting}
        onClick={() => onSubmit(isChoice ? (choice ?? "") : text.trim())}
      >
        {submitting ? "Saving…" : "Next"}
      </Button>
    </div>
  );
}

function CompleteStep() {
  return (
    <Card>
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-brand)]/15 text-2xl">
        ✓
      </div>
      <h2 className="mt-5 text-center text-xl font-semibold">
        Profile is ready
      </h2>
      <p className="mt-2 text-center text-sm text-[var(--color-fg-muted)]">
        We learned enough to start tutoring you the way that works.
      </p>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
        <Link href="/chat">
          <Button size="lg" className="w-full sm:w-auto">
            Start chatting →
          </Button>
        </Link>
        <Link href="/profile">
          <Button size="lg" variant="outline" className="w-full sm:w-auto">
            See my profile
          </Button>
        </Link>
      </div>
    </Card>
  );
}

function FieldGroup({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-3">
      <p className="text-sm font-medium">{label}</p>
      {children}
    </div>
  );
}

function CenterMessage({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md items-center justify-center px-6 text-center text-sm text-[var(--color-fg-muted)]">
      {children}
    </main>
  );
}

