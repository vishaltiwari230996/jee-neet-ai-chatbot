"use client";

/**
 * Onboarding flow — questions live on the frontend.
 *
 * Step 1 (intake): pick class level + exam target.
 * Step 2 (questions): walk through the hardcoded list filtered by exam.
 * Step 3 (save): POST the consolidated profile to the backend, then go
 *                to /chat.
 *
 * No backend question bank, no per-question round trips, no Clerk gates.
 * If something breaks mid-flow, refresh and pick up from the same questions.
 */

import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { RadioGroup } from "@/components/ui/radio-group";
import { TextInput } from "@/components/ui/text-input";
import { ApiError, api } from "@/lib/api/client";
import type {
  ClassLevel,
  ExamTarget,
  ProfileUpsertRequest,
} from "@/lib/api/types";
import {
  type OnboardingQuestion,
  questionsForExam,
} from "@/lib/onboarding-questions";
import { useStudentId } from "@/lib/student";

const CLASS_LEVELS: ClassLevel[] = ["class_11", "class_12", "dropper"];
const EXAM_TARGETS: ExamTarget[] = [
  "jee_main",
  "jee_advanced",
  "neet",
  "jee_main_advanced",
];

interface Answers {
  [field: string]: string | number | undefined;
}

type Phase = "intake" | "questions" | "saving" | "done" | "error";

export default function OnboardingPage() {
  const router = useRouter();
  const studentId = useStudentId();

  const [classLevel, setClassLevel] = useState<ClassLevel | null>(null);
  const [examTarget, setExamTarget] = useState<ExamTarget | null>(null);
  const [phase, setPhase] = useState<Phase>("intake");
  const [questionIdx, setQuestionIdx] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const questions = useMemo<OnboardingQuestion[]>(
    () => (examTarget ? questionsForExam(examTarget) : []),
    [examTarget],
  );

  if (!studentId) {
    return <Center>Preparing your session…</Center>;
  }

  if (phase === "saving") {
    return <Center>Saving your profile…</Center>;
  }

  if (phase === "done") {
    return <Center>All set. Opening chat…</Center>;
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col px-5 py-10 sm:py-16">
      <Header />

      {phase === "intake" ? (
        <IntakeStep
          classLevel={classLevel}
          examTarget={examTarget}
          onClassLevel={setClassLevel}
          onExamTarget={setExamTarget}
          onContinue={() => {
            if (!classLevel || !examTarget) return;
            setPhase("questions");
            setQuestionIdx(0);
            setAnswers({});
          }}
        />
      ) : null}

      {phase === "questions" && classLevel && examTarget ? (
        <QuestionStep
          question={questions[questionIdx]}
          index={questionIdx}
          total={questions.length}
          onAnswer={(value) => {
            const current = questions[questionIdx];
            if (!current) return;
            const nextAnswers: Answers = {
              ...answers,
              [current.field]: value,
            };
            setAnswers(nextAnswers);

            if (questionIdx + 1 < questions.length) {
              setQuestionIdx(questionIdx + 1);
              return;
            }

            void submitProfile({
              studentId,
              classLevel,
              examTarget,
              answers: nextAnswers,
              setPhase,
              setErrorMessage,
              router,
            });
          }}
          onBack={() => {
            if (questionIdx === 0) {
              setPhase("intake");
              return;
            }
            setQuestionIdx(questionIdx - 1);
          }}
        />
      ) : null}

      {phase === "error" ? (
        <Card className="text-center">
          <h2 className="text-lg font-semibold">Could not save your profile</h2>
          <p className="mt-2 text-sm text-[var(--color-danger)]">
            {errorMessage ?? "Unknown error"}
          </p>
          <div className="mt-4 flex justify-center gap-3">
            <Button
              onClick={() => {
                setPhase("questions");
                setErrorMessage(null);
              }}
            >
              Try again
            </Button>
            <Link href="/">
              <Button variant="outline">Home</Button>
            </Link>
          </div>
        </Card>
      ) : null}
    </main>
  );
}

interface SubmitArgs {
  studentId: string;
  classLevel: ClassLevel;
  examTarget: ExamTarget;
  answers: Answers;
  setPhase: (p: Phase) => void;
  setErrorMessage: (m: string | null) => void;
  router: ReturnType<typeof useRouter>;
}

async function submitProfile(args: SubmitArgs) {
  const { studentId, classLevel, examTarget, answers, setPhase, setErrorMessage, router } = args;
  setPhase("saving");
  try {
    const body: ProfileUpsertRequest = {
      student_id: studentId,
      class_level: classLevel,
      exam_target: examTarget,
      weak_subject: optionalString(answers.weak_subject),
      strong_subject: optionalString(answers.strong_subject),
      learning_style: optionalString(answers.learning_style),
      mock_score_range: optionalString(answers.mock_score_range),
      main_problem: optionalString(answers.main_problem),
      mistake_pattern: optionalString(answers.mistake_pattern),
      emotional_state: optionalString(answers.emotional_state),
      revision_habit: optionalString(answers.revision_habit),
      study_hours_per_day: optionalNumber(answers.study_hours_per_day),
    };
    await api.upsertProfile(body);
    setPhase("done");
    router.push("/chat");
  } catch (err) {
    setErrorMessage(
      err instanceof ApiError
        ? err.message
        : "Something went wrong. Please try again.",
    );
    setPhase("error");
  }
}

function optionalString(value: string | number | undefined): string | undefined {
  if (value === undefined || value === null) return undefined;
  const text = String(value).trim();
  return text.length > 0 ? text : undefined;
}

function optionalNumber(value: string | number | undefined): number | undefined {
  if (value === undefined || value === null || value === "") return undefined;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

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
  onContinue,
}: {
  classLevel: ClassLevel | null;
  examTarget: ExamTarget | null;
  onClassLevel: (v: ClassLevel) => void;
  onExamTarget: (v: ExamTarget) => void;
  onContinue: () => void;
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
          disabled={!ready}
          onClick={onContinue}
        >
          Continue
        </Button>
      </div>
    </Card>
  );
}

function QuestionStep({
  question,
  index,
  total,
  onAnswer,
  onBack,
}: {
  question: OnboardingQuestion | undefined;
  index: number;
  total: number;
  onAnswer: (value: string | number) => void;
  onBack: () => void;
}) {
  const [choice, setChoice] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [num, setNum] = useState("");

  useEffect(() => {
    setChoice(null);
    setText("");
    setNum("");
  }, [question?.id]);

  if (!question) {
    return (
      <Card className="text-center">
        <p className="text-sm text-[var(--color-fg-muted)]">
          No questions configured for this exam.
        </p>
      </Card>
    );
  }

  const canSubmit =
    question.type === "single_choice"
      ? choice !== null
      : question.type === "number"
        ? num.trim().length > 0
        : text.trim().length > 0;

  return (
    <Card>
      <Progress
        value={(index + 1) / total}
        label={`Step ${index + 1} of ${total}`}
      />

      <h2 className="mt-6 text-[17px] font-medium leading-7">
        {question.text}
      </h2>

      <div className="mt-6">
        {question.type === "single_choice" ? (
          <RadioGroup
            name={question.id}
            options={question.options ?? []}
            value={choice}
            onChange={setChoice}
          />
        ) : question.type === "number" ? (
          <TextInput
            value={num}
            onChange={(e) =>
              setNum(e.target.value.replace(/[^0-9.]/g, ""))
            }
            placeholder="e.g. 5"
          />
        ) : (
          <TextInput
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type your answer…"
          />
        )}
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-between">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button
          disabled={!canSubmit}
          onClick={() => {
            if (question.type === "single_choice" && choice !== null) {
              onAnswer(choice);
            } else if (question.type === "number" && num.trim()) {
              onAnswer(Number(num));
            } else if (text.trim()) {
              onAnswer(text.trim());
            }
          }}
        >
          {index + 1 === total ? "Finish" : "Next"}
        </Button>
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

function Center({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md items-center justify-center px-6 text-center text-sm text-[var(--color-fg-muted)]">
      {children}
    </main>
  );
}
