"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

export function LoginButtons({
  createLabel = "Create account",
  allowSignIn = true,
}: {
  createLabel?: string;
  allowSignIn?: boolean;
}) {
  const { configured, signInWithGoogle, signInWithEmail, signUpWithEmail } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"create" | "signin">("create");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!configured) {
    return (
      <p className="text-sm text-muted-foreground">
        Auth keys are not set. Add <code>NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
        <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> to enable Email and Google sign-in.
      </p>
    );
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      if (mode === "signin") {
        await signInWithEmail(email.trim(), password);
      } else {
        const result = await signUpWithEmail(email.trim(), password);
        if (result.needsConfirm) {
          setMessage("Check your email to confirm the account, then sign in.");
        }
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <Button
        type="button"
        className="w-full"
        disabled={busy}
        onClick={() => {
          setError(null);
          void signInWithGoogle().catch((caught: unknown) => {
            setError(caught instanceof Error ? caught.message : "Google sign-in failed.");
          });
        }}
      >
        Continue with Google
      </Button>
      <div className="flex items-center gap-3 text-xs uppercase tracking-wide text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        or
        <span className="h-px flex-1 bg-border" />
      </div>
      <form className="space-y-3" onSubmit={(event) => void onSubmit(event)}>
        <label className="block text-xs text-muted-foreground">
          Email
          <input
            type="email"
            required
            autoComplete="email"
            className="mt-1 h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className="block text-xs text-muted-foreground">
          Password
          <input
            type="password"
            required
            minLength={6}
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
            className="mt-1 h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <Button type="submit" className="w-full" variant="brown" disabled={busy}>
          {mode === "signin" ? "Sign in" : createLabel}
        </Button>
      </form>
      {allowSignIn ? (
        <button
          type="button"
          className="w-full text-center text-xs text-muted-foreground underline-offset-4 hover:underline"
          onClick={() => setMode(mode === "create" ? "signin" : "create")}
        >
          {mode === "create" ? "Already have an account? Sign in" : "Need an account? Create one"}
        </button>
      ) : null}
      {message ? <p className="text-sm text-accent-green">{message}</p> : null}
      {error ? <p className="text-sm text-accent-brown">{error}</p> : null}
    </div>
  );
}
