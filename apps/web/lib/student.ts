"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

/**
 * Student identity, bound to the signed-in Clerk user.
 *
 * Returns `null` while Clerk is still loading or the user is signed out.
 * Once we have a user, the student id is `stu_<clerk-user-id>` — that's
 * what the backend stores in Postgres and uses for personalisation.
 *
 * We prefix with `stu_` so the format stays compatible with the rows the
 * pre-auth localhost demo created. The shape is documented in
 * `apps/api/.../onboarding.py` (StartOnboardingRequest.student_id).
 */
export function useStudentId(): string | null {
  const { isLoaded, isSignedIn, userId } = useAuth();
  if (!isLoaded || !isSignedIn || !userId) return null;
  return `stu_${userId}`;
}

/**
 * Display name for the signed-in user — used in greetings and on the
 * profile screen. Returns the user's first name, full name, or email
 * local-part in that order, or `null` while loading / signed out.
 */
export function useStudentName(): string | null {
  const { isLoaded, user } = useUser();
  if (!isLoaded || !user) return null;
  if (user.firstName) return user.firstName;
  if (user.fullName) return user.fullName;
  const email = user.primaryEmailAddress?.emailAddress;
  if (email) return email.split("@")[0] ?? email;
  return "there";
}

/**
 * After-mount hook: returns true once Clerk has resolved the session
 * (regardless of signed-in state). Use to gate UI that needs to know
 * "signed in or not" instead of "loading".
 */
export function useAuthReady(): boolean {
  const { isLoaded } = useAuth();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (isLoaded) setReady(true);
  }, [isLoaded]);
  return ready;
}
