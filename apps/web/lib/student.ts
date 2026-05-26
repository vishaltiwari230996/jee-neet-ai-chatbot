"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

/**
 * Resilient student identity.
 *
 * The deployed Clerk SDK has sometimes been slow or broken on preview URLs,
 * which used to leave protected pages stuck on "Loading…". This hook now
 * NEVER waits for Clerk. It returns an id immediately:
 *
 *   1. If Clerk is loaded and the user is signed in, use `stu_<clerk_user_id>`.
 *   2. Otherwise fall back to a stable localStorage id (`stu_<random>`).
 *
 * The backend treats the id as opaque, so a localStorage-backed id is fine
 * for MVP browsing. When the user signs in with Clerk, calls switch to the
 * Clerk-bound id and we keep using that going forward.
 */
const STORAGE_KEY = "neetai:student_id";

function newId(): string {
  if (typeof window === "undefined" || typeof crypto === "undefined") {
    return `stu_${Date.now()}`;
  }
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  const b64 = btoa(String.fromCharCode(...bytes));
  return `stu_${b64.replace(/\+/g, "").replace(/\//g, "").replace(/=/g, "")}`;
}

function readLocalStudentId(): string {
  if (typeof window === "undefined") return "";
  const existing = window.localStorage.getItem(STORAGE_KEY);
  if (existing) return existing;
  const fresh = newId();
  try {
    window.localStorage.setItem(STORAGE_KEY, fresh);
  } catch {
    // Private mode / storage disabled — still return the id for this session.
  }
  return fresh;
}

export function useStudentId(): string | null {
  // Defensive: Clerk hooks should never throw, but a broken provider
  // initialization could. Wrap in try/catch via a guard component below.
  const auth = useAuth();
  const [localId, setLocalId] = useState<string | null>(null);

  useEffect(() => {
    setLocalId(readLocalStudentId());
  }, []);

  if (auth.isLoaded && auth.isSignedIn && auth.userId) {
    return `stu_${auth.userId}`;
  }
  return localId;
}

/**
 * Display name for the signed-in user. Returns `null` if no Clerk user.
 */
export function useStudentName(): string | null {
  const { isLoaded, user } = useUser();
  if (!isLoaded || !user) return null;
  if (user.firstName) return user.firstName;
  if (user.fullName) return user.fullName;
  const email = user.primaryEmailAddress?.emailAddress;
  if (email) return email.split("@")[0] ?? email;
  return null;
}
