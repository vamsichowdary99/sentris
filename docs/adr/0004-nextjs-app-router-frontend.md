# ADR 0004: Next.js 15 App Router + React Query + Zustand for the frontend

## Status
Accepted

## Context
The frontend needed: a protected app shell (dashboard/alerts/cases/
investigate) behind auth, a public landing + login flow, server-friendly
routing, and a lot of async server state (alerts, cases, AI analyses,
investigate results) alongside a small amount of genuine client state
(sidebar open/closed, the persisted auth token). The realistic
alternatives were Next.js Pages Router, a plain Vite + React SPA, or
Remix.

## Decision
Next.js 15 App Router with TypeScript and Tailwind for structure/styling,
`@tanstack/react-query` for all server state, and Zustand (with the
`persist` middleware) for the small slice of real client state — auth
tokens and the mobile sidebar toggle.

## Rationale
- **Route groups map cleanly onto the auth boundary.** `app/(app)/` holds
  everything behind the protected shell (its `layout.tsx` redirects to
  `/login` once the persisted auth store has hydrated and no token is
  present); `app/login/` and `app/page.tsx` (the landing page) stay
  outside it. No route-level auth middleware to hand-roll.
- **React Query, not hand-rolled `useEffect` fetching, for every API
  call.** Cache invalidation after a mutation (e.g. `PATCH /alerts/{id}`
  invalidating the alert-detail and alerts-list queries) is declarative,
  and it's what makes the AI Copilot panel, the Investigate page, and
  the case report card all re-render correctly after a POST without any
  manual state plumbing.
- **Zustand only for what's actually client state.** The auth store
  (`lib/auth-store.ts`) persists `accessToken`/`refreshToken`/`user`/
  `roles`/`permissions` to `localStorage` via the `persist` middleware,
  with a `hydrated` flag the app shell waits on before deciding whether
  to redirect — avoiding a flash-of-login-page on reload. Server data
  (alerts, cases, AI output) is deliberately *not* duplicated into
  Zustand; React Query already owns it.
- **`next/font/google` for self-hosted fonts** (Fraunces/IBM Plex Sans/
  IBM Plex Mono) keeps the dark, terminal-adjacent design system's
  typography loading without a runtime request to Google Fonts.

## Consequences
- Docker's bind-mounted volumes on Windows don't reliably propagate
  Next.js's file-watch events — a config or component edit sometimes
  needs `docker compose restart frontend` to be picked up in dev. A
  documented, known gotcha rather than a design flaw, but worth calling
  out since it cost real debugging time across phases.
- The API client (`lib/api.ts`) hand-rolls 401 → refresh-and-retry
  (deduped via a module-level in-flight promise) rather than using a
  heavier data-fetching framework's built-in interceptor story — a
  deliberately small, auditable ~90-line file over a dependency.
- No server components do data fetching in this codebase — every
  data-bearing page is a client component using React Query. This trades
  away some of the App Router's SSR/streaming story in exchange for one
  consistent mental model (and one auth story: the browser holds the
  token, not a server-side session) across the whole app. Revisit if a
  future phase adds SSR-sensitive pages (e.g. a public shareable case
  report).
