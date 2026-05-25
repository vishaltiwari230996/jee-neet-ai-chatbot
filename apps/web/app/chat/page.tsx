"use client";

import Link from "next/link";
import {
  type FormEvent,
  type KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { UserButton } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StructuredAnswer } from "@/components/chat/structured-answer";
import { ApiError, api } from "@/lib/api/client";
import { streamChat } from "@/lib/api/chat";
import type { ChatMessage, Language, ProfileSummary } from "@/lib/api/types";
import { useStudentId } from "@/lib/student";

/**
 * MVP chat surface.
 *
 * Conversation history is held in React state — refresh resets the thread.
 * That's intentional for v1: persistence is the next chunk of work and would
 * not change anything visible on this page. When `ChatRepository` lands we
 * just swap the `messages` source for a React Query subscription.
 *
 * Why the input is a textarea, not an `<input>`:
 *   * planning questions run long; "I have 4 hours/day, weak Physics, and
 *     6 months left — how should I revise?" doesn't fit a single line on mobile
 *   * Cmd/Ctrl+Enter to send, Enter for newline — matches every modern chat UX
 */

interface ChatMessageState extends ChatMessage {
  /** True while the assistant is still streaming this message in. */
  pending?: boolean;
  /** Set if this turn failed. Rendered inline so the user has a way to retry. */
  error?: string;
}

const LANGUAGES: Array<{ value: Language; label: string }> = [
  { value: "en", label: "English" },
  { value: "hi", label: "हिंदी" },
  { value: "hi-en", label: "Hinglish" },
];

export default function ChatPage() {
  const studentId = useStudentId();

  const profileQuery = useQuery<ProfileSummary | null>({
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

  const [messages, setMessages] = useState<ChatMessageState[]>([]);
  const [draft, setDraft] = useState("");
  const [language, setLanguage] = useState<Language>("en");
  const [isSending, setIsSending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  async function send() {
    const text = draft.trim();
    if (!text || isSending || !studentId) return;
    const sid = studentId;

    const userMsg: ChatMessageState = { role: "user", content: text };
    const assistantIdx = messages.length + 1;
    setMessages((prev) => [
      ...prev,
      userMsg,
      { role: "assistant", content: "", pending: true },
    ]);
    setDraft("");
    setIsSending(true);

    const history: ChatMessage[] = messages
      .filter((m) => !m.error)
      .map((m) => ({ role: m.role, content: m.content }));

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      let acc = "";
      for await (const event of streamChat(
        { student_id: sid, question: text, history, language },
        controller.signal,
      )) {
        if (event.kind === "delta") {
          acc += event.text;
          setMessages((prev) => {
            const copy = prev.slice();
            copy[assistantIdx] = {
              role: "assistant",
              content: acc,
              pending: true,
            };
            return copy;
          });
        } else if (event.kind === "error") {
          setMessages((prev) => {
            const copy = prev.slice();
            copy[assistantIdx] = {
              role: "assistant",
              content: acc,
              error: event.message,
            };
            return copy;
          });
        } else if (event.kind === "done") {
          setMessages((prev) => {
            const copy = prev.slice();
            copy[assistantIdx] = { role: "assistant", content: acc };
            return copy;
          });
        }
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof DOMException && err.name === "AbortError"
            ? "Cancelled."
            : "Something went wrong while streaming. Try again.";
      setMessages((prev) => {
        const copy = prev.slice();
        const last = copy[assistantIdx];
        copy[assistantIdx] = {
          role: "assistant",
          content: last?.content ?? "",
          error: message,
        };
        return copy;
      });
    } finally {
      setIsSending(false);
      abortRef.current = null;
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send();
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void send();
    }
  }

  function stop() {
    abortRef.current?.abort();
  }

  const noProfile = !profileQuery.isLoading && !profileQuery.data;

  return (
    <main className="mx-auto flex h-dvh max-w-3xl flex-col px-4 sm:px-6">
      <header className="flex items-center justify-between border-b border-[var(--color-border)] py-4">
        <Link
          href="/"
          className="text-sm text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
        >
          ← Home
        </Link>
        <div className="flex items-center gap-3">
          {profileQuery.data ? (
            <ProfileChip profile={profileQuery.data} />
          ) : null}
          <Link
            href="/profile"
            className="text-xs text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
          >
            Profile
          </Link>
          <UserButton />
        </div>
      </header>

      <div className="flex items-center justify-between gap-3 border-b border-[var(--color-border)] py-3">
        <span className="text-xs uppercase tracking-wider text-[var(--color-fg-muted)]">
          Response language
        </span>
        <div className="inline-flex rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-1">
          {LANGUAGES.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setLanguage(option.value)}
              className={
                language === option.value
                  ? "rounded-lg bg-[var(--color-brand-strong)] px-3 py-1.5 text-xs font-medium text-white"
                  : "rounded-lg px-3 py-1.5 text-xs text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
              }
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div
        ref={scrollerRef}
        className="flex-1 overflow-y-auto py-6"
        aria-live="polite"
      >
        {noProfile ? <ProfileMissingPrompt /> : null}

        {!noProfile && messages.length === 0 ? (
          <EmptyState archetype={profileQuery.data?.archetype} />
        ) : null}

        <div className="space-y-6">
          {messages.map((m, idx) => (
            <Message key={idx} message={m} />
          ))}
        </div>
      </div>

      <form
        onSubmit={onSubmit}
        className="border-t border-[var(--color-border)] py-4"
      >
        <div className="flex items-end gap-3">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={
              noProfile
                ? "Finish onboarding first to start chatting."
                : "Ask for strategy — e.g. I have 4 hours/day and weak Physics. Make me a 2-week plan."
            }
            disabled={isSending || noProfile}
            rows={1}
            className="min-h-[44px] max-h-40 flex-1 resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-4 py-3 text-[15px] text-[var(--color-fg)] outline-none placeholder:text-[var(--color-fg-muted)] focus:border-[var(--color-brand)] disabled:opacity-50"
          />
          {isSending ? (
            <Button type="button" variant="outline" onClick={stop}>
              Stop
            </Button>
          ) : (
            <Button type="submit" disabled={!draft.trim() || noProfile}>
              Send
            </Button>
          )}
        </div>
        <p className="mt-2 text-[11px] text-[var(--color-fg-muted)]">
          ⌘/Ctrl + Enter to send. EduGuide AI gives study strategy, not solved
          answers. Language: {languageLabel(language)}. Verify official exam
          info on NTA / JoSAA / MCC websites.
        </p>
      </form>
    </main>
  );
}

function languageLabel(language: Language): string {
  return LANGUAGES.find((option) => option.value === language)?.label ?? "English";
}

function Message({ message }: { message: ChatMessageState }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl bg-[var(--color-brand-strong)] px-4 py-2.5 text-[15px] text-white">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <Card className="max-w-[92%] !p-4 sm:!p-5">
        <StructuredAnswer
          text={message.content}
          streaming={message.pending && !message.error}
        />
        {message.error ? (
          <p className="mt-3 rounded-md border border-[var(--color-danger)]/40 bg-[var(--color-danger)]/10 px-3 py-2 text-xs text-[var(--color-danger)]">
            {message.error}
          </p>
        ) : null}
      </Card>
    </div>
  );
}

function ProfileChip({ profile }: { profile: ProfileSummary }) {
  return (
    <span className="hidden rounded-full border border-[var(--color-border)] px-3 py-1 text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)] sm:inline">
      {profile.archetype.replace(/_/g, " ")}
    </span>
  );
}

function EmptyState({ archetype }: { archetype: string | undefined }) {
  const examples = [
    "Make me a 2-week revision plan for weak Physics.",
    "How should I analyze my mock test mistakes?",
    "I keep forgetting formulas — build me a spaced-revision routine.",
  ];
  return (
    <div className="mx-auto max-w-xl text-center">
      <h2 className="text-2xl font-semibold">Plan smarter for JEE/NEET.</h2>
      <p className="mt-2 text-sm text-[var(--color-fg-muted)]">
        {archetype
          ? "Tuned to your profile. Ask for a plan, revision system, or mock-analysis strategy."
          : "Try one of these, or type your own strategy question."}
      </p>
      <ul className="mt-6 grid gap-2">
        {examples.map((q) => (
          <li
            key={q}
            className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-4 py-3 text-left text-sm text-[var(--color-fg-muted)]"
          >
            {q}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ProfileMissingPrompt() {
  return (
    <Card className="mx-auto max-w-md text-center">
      <h2 className="text-lg font-semibold">Finish onboarding first</h2>
      <p className="mt-2 text-sm text-[var(--color-fg-muted)]">
        Personalised chat needs your profile. It takes about three minutes.
      </p>
      <Link href="/onboarding" className="mt-4 inline-block">
        <Button size="md">Start onboarding</Button>
      </Link>
    </Card>
  );
}
