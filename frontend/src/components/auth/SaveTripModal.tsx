"use client";

import { WARM_GENERATION_TIMEOUT_MS, type SavedTrip } from "@cuvoy/contracts";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { LoginButtons } from "@/components/auth/LoginButtons";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { usePlanSessionOptional } from "@/context/PlanSessionContext";
import { PlanApiError } from "@/lib/planApi";
import { saveTrip } from "@/lib/tripApi";

export function SaveTripModal() {
  const { user, accessToken, modalOpen, modalIntent, closeAuth } = useAuth();
  const session = usePlanSessionOptional();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [saved, setSaved] = useState<SavedTrip | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const planId = session?.planId ?? null;
  const defaultTitle =
    session?.result?.itinerary.days[0]?.city != null
      ? `Trip to ${session.result.itinerary.days[0].city}`
      : "Saved trip";

  useEffect(() => {
    if (!modalOpen) {
      setSaved(null);
      setError(null);
      setCopied(false);
      setTitle("");
    }
  }, [modalOpen]);

  useEffect(() => {
    if (modalOpen && !title && defaultTitle) {
      setTitle(defaultTitle);
    }
  }, [defaultTitle, modalOpen, title]);

  if (!modalOpen) {
    return null;
  }

  const heading =
    modalIntent === "login" ? "Log in to CuVoy" : modalIntent === "share" ? "Share your trip" : "Save your trip";

  async function persist() {
    if (!planId) {
      setError("Generate a trip first, then save or share it.");
      return;
    }
    if (!user?.id || !accessToken) {
      setError("Session expired. Sign in again.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const trip = await saveTrip(
        { plan_id: planId, title: title.trim() || null, user_id: user.id },
        WARM_GENERATION_TIMEOUT_MS,
        session?.result ?? null,
        accessToken,
      );
      setSaved(trip);
      await queryClient.invalidateQueries({ queryKey: ["trips"] });
    } catch (caught) {
      if (caught instanceof PlanApiError && caught.status === 401) {
        setError("Session expired. Sign in again.");
      } else {
        setError(caught instanceof Error ? caught.message : "Could not save this trip.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function copyShare() {
    const url = saved?.share_url;
    if (!url) {
      return;
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        className="w-full max-w-sm rounded-md border border-border bg-card p-5 shadow-sm"
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="auth-modal-title" className="text-lg font-semibold">
            {heading}
          </h2>
          <button
            type="button"
            className="text-sm text-muted-foreground hover:text-foreground"
            onClick={closeAuth}
          >
            Close
          </button>
        </div>
        <div className="mt-4">
          {!user ? (
            <>
              {modalIntent !== "login" ? (
                <p className="mb-4 text-sm text-muted-foreground">
                  Saving and sharing require an account. Anonymous planning still works.
                </p>
              ) : null}
              <LoginButtons />
            </>
          ) : saved ? (
            <div className="space-y-3">
              <p className="text-sm">Saved as {saved.title}.</p>
              {saved.share_url ? (
                <p className="break-all rounded-md border border-border bg-muted px-3 py-2 text-xs">
                  {saved.share_url}
                </p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <Button type="button" size="sm" onClick={() => void copyShare()}>
                  {copied ? "Copied" : "Copy share link"}
                </Button>
                <Button type="button" size="sm" variant="outline" onClick={closeAuth}>
                  Done
                </Button>
              </div>
            </div>
          ) : modalIntent === "login" ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">Signed in as {user.email ?? "your account"}.</p>
              <Button type="button" className="w-full" onClick={closeAuth}>
                Continue
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">Signed in as {user.email ?? "your account"}.</p>
              <label className="block text-xs text-muted-foreground">
                Trip title
                <input
                  className="mt-1 h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                />
              </label>
              <Button type="button" className="w-full" disabled={busy || !planId} onClick={() => void persist()}>
                {modalIntent === "share" ? "Save and get share link" : "Save trip"}
              </Button>
              {!planId ? (
                <p className="text-xs text-muted-foreground">Open a completed itinerary to save it.</p>
              ) : null}
            </div>
          )}
          {error ? <p className="mt-3 text-sm text-accent-brown">{error}</p> : null}
        </div>
      </div>
    </div>
  );
}
