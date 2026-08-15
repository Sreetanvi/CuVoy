"use client";

import {
  COLD_START_CLIENT_TIMEOUT_MS,
  COLD_START_UI_MESSAGE,
  WARM_GENERATION_TIMEOUT_MS,
} from "@cuvoy/contracts";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { pingHealth } from "@/lib/api";

const SLOW_THRESHOLD_MS = 2500;

export type ColdStartStatus = "idle" | "waking" | "warm" | "failed";

export function useColdStart() {
  const [status, setStatus] = useState<ColdStartStatus>("idle");
  const [elapsedMs, setElapsedMs] = useState(0);
  const startedAt = useRef<number | null>(null);
  const slowTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearSlowTimer = () => {
    if (slowTimer.current) {
      clearTimeout(slowTimer.current);
      slowTimer.current = null;
    }
  };

  const ping = useCallback(async () => {
    clearSlowTimer();
    startedAt.current = performance.now();
    setElapsedMs(0);
    setStatus("idle");
    slowTimer.current = setTimeout(() => {
      setStatus("waking");
    }, SLOW_THRESHOLD_MS);

    try {
      await pingHealth(COLD_START_CLIENT_TIMEOUT_MS);
      const duration = performance.now() - (startedAt.current ?? performance.now());
      setElapsedMs(duration);
      setStatus("warm");
    } catch {
      setStatus("failed");
    } finally {
      clearSlowTimer();
    }
  }, []);

  useEffect(() => {
    void ping();
    return () => clearSlowTimer();
  }, [ping]);

  const requestTimeoutMs =
    status === "warm" ? WARM_GENERATION_TIMEOUT_MS : COLD_START_CLIENT_TIMEOUT_MS;

  return useMemo(
    () => ({
      status,
      waking: status === "waking",
      warm: status === "warm",
      failed: status === "failed",
      message: COLD_START_UI_MESSAGE,
      elapsedMs,
      requestTimeoutMs,
      retry: ping,
    }),
    [elapsedMs, ping, requestTimeoutMs, status],
  );
}
