# @neetai/web

Next.js 15 frontend for the NeetAI tutor.

## Architecture

* **Routing:** App Router (RSC by default; client islands where state lives).
* **Styling:** Tailwind v4 with a small set of CSS variables for theme tokens.
* **Data:** TanStack Query + a tiny typed `apiClient` in `lib/api/`.
* **API access:** all `/api/*` calls are proxied to FastAPI via the
  `next.config.mjs` rewrite, so there's no CORS to manage in dev.
* **Identity:** localStorage-backed `student_id` in `lib/student.ts`.
  This is a deliberate stub; Clerk slots in by deleting this file and
  reading `useUser().id` instead.

## Scripts

```bash
pnpm dev          # localhost:3000, proxies /api/* to localhost:8000
pnpm build        # production build
pnpm typecheck    # tsc --noEmit
pnpm lint         # next lint
pnpm gen:api      # regenerate openapi types (requires the API running)
```

## Page map

| Route          | Purpose                                                |
| -------------- | ------------------------------------------------------ |
| `/`            | Landing page; CTA into onboarding                       |
| `/onboarding`  | Intake + adaptive diagnostic loop; resume-safe          |
| `/profile`     | Read-only view of the profile + missing-field tracker  |

## Adding a new page that talks to the API

1. Add the endpoint to `lib/api/client.ts`.
2. Add request/response types to `lib/api/types.ts` (or regenerate via
   `pnpm gen:api` once you've decided to lean on OpenAPI).
3. Use `useQuery` / `useMutation` from `@tanstack/react-query`. Errors
   come back typed as `ApiError` — render `error.message` directly.
