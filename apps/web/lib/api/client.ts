/**
 * Thin typed client around the NeetAI HTTP API.
 *
 * Two reasons it's hand-written instead of a giant generated SDK:
 *   1. The MVP surface is small (3 endpoints). A 1 KB wrapper beats a
 *      200 KB generated client we'd have to maintain.
 *   2. Errors are translated into typed `ApiError` instances, so React
 *      components can `try/catch` against a known shape instead of
 *      sniffing fetch responses.
 *
 * All requests go through Next.js's `/api/*` rewrite proxy (see
 * `next.config.mjs`), so we don't deal with CORS in dev. Production
 * deploys would set `NEXT_PUBLIC_API_BASE` instead.
 */

import type {
  ApiErrorBody,
  OnboardingStateResponse,
  ProfileSummary,
  ProfileUpsertRequest,
  StartOnboardingRequest,
  SubmitAnswerRequest,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.code = body.code;
    this.name = "ApiError";
  }
}

async function request<T>(
  method: "GET" | "POST",
  path: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });

  if (!res.ok) {
    let parsed: ApiErrorBody;
    try {
      parsed = (await res.json()) as ApiErrorBody;
    } catch {
      parsed = {
        code: "network_error",
        message: `Request to ${path} failed (${res.status})`,
      };
    }
    throw new ApiError(res.status, parsed);
  }

  return (await res.json()) as T;
}

export const api = {
  startOnboarding: (body: StartOnboardingRequest) =>
    request<OnboardingStateResponse>("POST", "/api/v1/onboarding/start", body),

  submitAnswer: (body: SubmitAnswerRequest) =>
    request<OnboardingStateResponse>("POST", "/api/v1/onboarding/answer", body),

  getOnboardingState: (studentId: string) =>
    request<OnboardingStateResponse>(
      "GET",
      `/api/v1/onboarding/state/${encodeURIComponent(studentId)}`,
    ),

  getProfile: (studentId: string) =>
    request<ProfileSummary>(
      "GET",
      `/api/v1/profile/${encodeURIComponent(studentId)}`,
    ),

  upsertProfile: (body: ProfileUpsertRequest) =>
    request<ProfileSummary>("POST", "/api/v1/profile/upsert", body),

  health: () => request<{ status: string }>("GET", "/health/live"),
};
