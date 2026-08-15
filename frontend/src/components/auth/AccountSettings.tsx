"use client";

import { WARM_GENERATION_TIMEOUT_MS } from "@cuvoy/contracts";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { LoginButtons } from "@/components/auth/LoginButtons";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { deleteAccount } from "@/lib/tripApi";

export function AccountSettings() {
  const { user, loading, signOut } = useAuth();
  const router = useRouter();
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (loading) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-2xl font-semibold">Profile settings</h1>
        <p className="mt-4 text-sm text-muted-foreground">Loading account…</p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-2xl font-semibold">Profile settings</h1>
        <p className="mt-4 mb-6 text-sm text-muted-foreground">
          Sign in to manage your account. You can delete your account and all saved trip data here.
        </p>
        <div className="max-w-sm">
          <LoginButtons />
        </div>
      </main>
    );
  }

  async function onDelete() {
    setBusy(true);
    setError(null);
    try {
      await deleteAccount(WARM_GENERATION_TIMEOUT_MS);
      await signOut();
      router.replace("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the account.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="text-2xl font-semibold">Profile settings</h1>
      <p className="mt-4 text-sm text-muted-foreground">Signed in as {user.email ?? user.id}.</p>
      <section className="mt-8 rounded-md border border-border p-4">
        <h2 className="text-sm font-medium">Delete account</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          This removes your CuVoy account and all saved trips (GDPR basic deletion). Type DELETE to
          confirm.
        </p>
        <input
          className="mt-3 h-10 w-full max-w-xs rounded-md border border-border bg-background px-3 text-sm"
          value={confirm}
          onChange={(event) => setConfirm(event.target.value)}
          placeholder="DELETE"
        />
        <Button
          type="button"
          variant="brown"
          className="mt-3"
          disabled={busy || confirm !== "DELETE"}
          onClick={() => void onDelete()}
        >
          Delete account and trips
        </Button>
        {error ? <p className="mt-3 text-sm text-accent-brown">{error}</p> : null}
      </section>
    </main>
  );
}
