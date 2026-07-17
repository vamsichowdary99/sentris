"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ApiError } from "@/lib/api";
import { useLogin, useRegister } from "@/lib/auth";
import { useAuthStore } from "@/lib/auth-store";

const DEMO_EMAIL = "demo@sentris.io";
const DEMO_PASSWORD = "demo12345";

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const register = useRegister();
  const hydrated = useAuthStore((s) => s.hydrated);
  const accessToken = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (hydrated && accessToken) router.replace("/dashboard");
  }, [hydrated, accessToken, router]);

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      if (mode === "register") {
        await register.mutateAsync({ email, password, full_name: fullName });
      }
      await login.mutateAsync({ email, password });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    }
  }

  function fillDemoCredentials() {
    setMode("login");
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASSWORD);
    setError(null);
  }

  const pending = login.isPending || register.isPending;

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-void px-6">
      <div className="pointer-events-none absolute inset-0 bg-signature-grid opacity-30 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />

      <div className="relative z-10 w-full max-w-sm">
        <Link href="/" className="mb-8 flex items-center justify-center gap-2">
          <span className="grid grid-cols-2 gap-0.5">
            <span className="h-1.5 w-1.5 rounded-[1px] bg-cyan" />
            <span className="h-1.5 w-1.5 rounded-[1px] bg-amber" />
            <span className="h-1.5 w-1.5 rounded-[1px] bg-amber" />
            <span className="h-1.5 w-1.5 rounded-[1px] bg-cyan" />
          </span>
          <span className="font-display text-xl tracking-tight text-paper">Sentris</span>
        </Link>

        <div className="rounded-lg border border-line bg-surface p-6">
          <h1 className="font-display text-xl text-paper">
            {mode === "login" ? "Sign in" : "Create an account"}
          </h1>
          <p className="mt-1 text-sm text-mist">
            {mode === "login"
              ? "Enter your credentials to reach the console."
              : "New analysts join as viewers of the demo org."}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            {mode === "register" && (
              <div>
                <label className="mb-1.5 block text-xs text-mist" htmlFor="full_name">
                  Full name
                </label>
                <input
                  id="full_name"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-md border border-line bg-surface-raised px-3 py-2 text-sm text-paper focus:border-cyan"
                />
              </div>
            )}
            <div>
              <label className="mb-1.5 block text-xs text-mist" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-line bg-surface-raised px-3 py-2 text-sm text-paper focus:border-cyan"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs text-mist" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-line bg-surface-raised px-3 py-2 text-sm text-paper focus:border-cyan"
              />
            </div>

            {error && (
              <p className="rounded-md border border-threat/40 bg-threat-dim/10 px-3 py-2 text-xs text-threat">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={pending}
              className="w-full rounded-md bg-cyan px-4 py-2 text-sm font-medium text-void transition-colors hover:bg-cyan/90 disabled:opacity-50"
            >
              {pending ? "Working…" : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>

          <button
            onClick={fillDemoCredentials}
            className="mt-4 w-full text-center font-mono text-[11px] text-mist hover:text-cyan"
          >
            Use demo credentials →
          </button>
        </div>

        <button
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
          }}
          className="mt-4 w-full text-center text-xs text-mist hover:text-paper"
        >
          {mode === "login" ? "Don't have an account? Register" : "Already have an account? Sign in"}
        </button>
      </div>
    </main>
  );
}
