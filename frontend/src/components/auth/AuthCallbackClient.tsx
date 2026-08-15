"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { readAuthResume } from "@/lib/auth";
import { getSupabaseBrowserClient } from "@/lib/supabase";

export function AuthCallbackClient() {
  const router = useRouter();
  const [message, setMessage] = useState("Completing sign-in…");

  useEffect(() => {
    const supabase = getSupabaseBrowserClient();
    if (!supabase) {
      setMessage("Supabase Auth is not configured.");
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const resume = readAuthResume();
    const next = resume?.returnTo || "/";

    void (async () => {
      try {
        if (code) {
          const { error } = await supabase.auth.exchangeCodeForSession(code);
          if (error) {
            setMessage(error.message);
            return;
          }
        }
        router.replace(next);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Sign-in failed.");
      }
    })();
  }, [router]);

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col justify-center px-6 py-12">
      <h1 className="text-2xl font-semibold">Signing in</h1>
      <p className="mt-3 text-sm text-muted-foreground">{message}</p>
    </main>
  );
}
