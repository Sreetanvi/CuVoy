"use client";

import {
  COLD_START_CLIENT_TIMEOUT_MS,
  SseEventSchema,
  WARM_GENERATION_TIMEOUT_MS,
  type PipelineStage,
  type PlanRequest,
  type PlanResult,
  type RegenerateRequest,
  type SseEvent,
} from "@cuvoy/contracts";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useColdStartContext } from "@/context/ColdStartContext";
import { useTripControls } from "@/context/TripControlsContext";
import {
  ApiTimeoutError,
  PlanApiError,
  createPlan,
  getPlan,
  getPlanStatus,
  planStatusStreamUrl,
  regeneratePlan,
} from "@/lib/planApi";
import { STAGE_COPY } from "@/lib/stageCopy";
import { getOwnedTrip } from "@/lib/tripApi";

export type PlanPhase = "idle" | "submitting" | "running" | "complete" | "error";

type PlanSessionValue = {
  readOnly: boolean;
  planId: string | null;
  result: PlanResult | null;
  phase: PlanPhase;
  progress: number;
  stage: PipelineStage | null;
  stageMessage: string | null;
  errorMessage: string | null;
  recoverable: boolean;
  creditRefunded: boolean;
  selectedDayIndex: number;
  setSelectedDayIndex: (index: number) => void;
  showFullTrip: boolean;
  setShowFullTrip: (value: boolean) => void;
  selectedPlaceId: string | null;
  setSelectedPlaceId: (id: string | null) => void;
  lockedStopIds: string[];
  skipStopIds: string[];
  toggleLock: (placeId: string) => void;
  toggleSkip: (placeId: string) => void;
  generate: (request: PlanRequest) => Promise<void>;
  regenerate: (patch?: Partial<RegenerateRequest>) => Promise<void>;
  loadPlan: (planId: string) => Promise<void>;
};

const PlanSessionContext = createContext<PlanSessionValue | null>(null);

function friendlyError(error: unknown, waking: boolean): string {
  if (waking || error instanceof ApiTimeoutError) {
    return "Waking up the AI planner…";
  }
  if (error instanceof PlanApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Planning failed. Try again.";
}

export function PlanSessionProvider({
  initialPlanId,
  initialResult,
  readOnly = false,
  children,
}: {
  initialPlanId?: string;
  initialResult?: PlanResult | null;
  readOnly?: boolean;
  children: React.ReactNode;
}) {
  const { requestTimeoutMs, waking, status: coldStatus, retry } = useColdStartContext();
  const { controls } = useTripControls();
  const [planId, setPlanId] = useState<string | null>(initialPlanId ?? null);
  const [result, setResult] = useState<PlanResult | null>(initialResult ?? null);
  const [phase, setPhase] = useState<PlanPhase>(initialResult ? "complete" : "idle");
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<PipelineStage | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [recoverable, setRecoverable] = useState(false);
  const [creditRefunded, setCreditRefunded] = useState(false);
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);
  const [showFullTrip, setShowFullTrip] = useState(false);
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  const [lockedStopIds, setLockedStopIds] = useState<string[]>([]);
  const [skipStopIds, setSkipStopIds] = useState<string[]>([]);
  const streamRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const planIdRef = useRef<string | null>(planId);

  planIdRef.current = planId;

  const stopWatching = useCallback(() => {
    streamRef.current?.close();
    streamRef.current = null;
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const applySse = useCallback((event: SseEvent) => {
    if (event.progress != null) {
      setProgress(event.progress);
    }
    if (event.stage) {
      setStage(event.stage);
    }
    if (event.event === "plan_error") {
      setPhase("error");
      setErrorMessage(event.error || "Planning failed");
      setRecoverable(Boolean(event.recoverable));
      setCreditRefunded(Boolean(event.credit_refunded));
      stopWatching();
    }
  }, [stopWatching]);

  const finishPlan = useCallback(
    async (id: string) => {
      try {
        const payload = await getPlan(id, WARM_GENERATION_TIMEOUT_MS);
        setResult(payload);
        setPhase("complete");
        setProgress(100);
        setSelectedDayIndex(0);
        stopWatching();
      } catch (error) {
        if (error instanceof PlanApiError && error.status === 409) {
          return;
        }
        setPhase("error");
        setErrorMessage(friendlyError(error, false));
        stopWatching();
      }
    },
    [stopWatching],
  );

  const watchPlan = useCallback(
    (id: string) => {
      stopWatching();
      setPhase("running");
      const source = new EventSource(planStatusStreamUrl(id));
      streamRef.current = source;

      const onPayload = (raw: MessageEvent<string>) => {
        try {
          const parsed = SseEventSchema.safeParse(JSON.parse(raw.data));
          if (!parsed.success) {
            return;
          }
          applySse(parsed.data);
          if (parsed.data.event === "plan_complete") {
            void finishPlan(id);
          }
        } catch {
          /* ignore malformed SSE frames */
        }
      };

      source.addEventListener("stage_start", onPayload);
      source.addEventListener("stage_complete", onPayload);
      source.addEventListener("plan_complete", onPayload);
      source.addEventListener("plan_error", onPayload);
      source.onmessage = onPayload;
      source.onerror = () => {
        source.close();
        streamRef.current = null;
      };

      pollRef.current = setInterval(() => {
        void (async () => {
          try {
            const status = await getPlanStatus(id, WARM_GENERATION_TIMEOUT_MS);
            setProgress(status.progress);
            if (status.stage) {
              setStage(status.stage);
            }
            if (status.status === "complete") {
              await finishPlan(id);
            }
            if (status.status === "failed") {
              setPhase("error");
              setErrorMessage("Planning failed. Try again.");
              setRecoverable(true);
              stopWatching();
            }
          } catch {
            /* poll continues until SSE or success */
          }
        })();
      }, 1500);
    },
    [applySse, finishPlan, stopWatching],
  );

  const generate = useCallback(
    async (request: PlanRequest) => {
      if (readOnly) {
        return;
      }
      setErrorMessage(null);
      setRecoverable(false);
      setCreditRefunded(false);
      setResult(null);
      setProgress(0);
      setStage(null);
      setPhase("submitting");
      setLockedStopIds([]);
      setSkipStopIds([]);
      if (coldStatus === "failed") {
        await retry();
      }
      const timeout =
        coldStatus === "warm" && !waking
          ? WARM_GENERATION_TIMEOUT_MS
          : Math.max(requestTimeoutMs, COLD_START_CLIENT_TIMEOUT_MS);
      try {
        const accepted = await createPlan(request, timeout, crypto.randomUUID());
        setPlanId(accepted.plan_id);
        watchPlan(accepted.plan_id);
        window.history.replaceState(null, "", `/plan/${accepted.plan_id}`);
      } catch (error) {
        setPhase("error");
        setErrorMessage(friendlyError(error, waking || coldStatus !== "warm"));
        setRecoverable(true);
      }
    },
    [coldStatus, readOnly, requestTimeoutMs, retry, waking, watchPlan],
  );

  const regenerate = useCallback(
    async (patch: Partial<RegenerateRequest> = {}) => {
      const id = planIdRef.current;
      if (!id || readOnly) {
        return;
      }
      setErrorMessage(null);
      setPhase("submitting");
      try {
        await regeneratePlan(
          id,
          {
            trip_controls: patch.trip_controls ?? controls,
            skip_stop_ids: patch.skip_stop_ids ?? skipStopIds,
            locked_stop_ids: patch.locked_stop_ids ?? lockedStopIds,
            swap: patch.swap ?? null,
            meal_override: patch.meal_override ?? null,
          },
          requestTimeoutMs,
        );
        watchPlan(id);
      } catch (error) {
        setPhase("error");
        setErrorMessage(friendlyError(error, waking));
        setRecoverable(true);
      }
    },
    [controls, lockedStopIds, readOnly, requestTimeoutMs, skipStopIds, waking, watchPlan],
  );

  const loadPlan = useCallback(
    async (id: string) => {
      setPlanId(id);
      setPhase("submitting");
      try {
        const payload = await getPlan(id, requestTimeoutMs);
        setResult(payload);
        setPhase("complete");
        setProgress(100);
      } catch (error) {
        if (error instanceof PlanApiError && error.status === 409) {
          watchPlan(id);
          return;
        }
        try {
          const owned = await getOwnedTrip(id, requestTimeoutMs);
          setResult(owned.result);
          setPlanId(owned.result.plan_id || owned.trip.plan_id || id);
          setPhase("complete");
          setProgress(100);
          return;
        } catch {
          setPhase("error");
          setErrorMessage(friendlyError(error, waking));
        }
      }
    },
    [requestTimeoutMs, waking, watchPlan],
  );

  useEffect(() => {
    if (initialResult || readOnly) {
      return;
    }
    if (initialPlanId) {
      void loadPlan(initialPlanId);
    }
    // Load once per plan id; loadPlan identity must not retrigger and abort SSE.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialPlanId]);

  useEffect(() => () => stopWatching(), [stopWatching]);

  const toggleLock = useCallback((placeId: string) => {
    setLockedStopIds((current) =>
      current.includes(placeId) ? current.filter((id) => id !== placeId) : [...current, placeId],
    );
  }, []);

  const toggleSkip = useCallback((placeId: string) => {
    setSkipStopIds((current) =>
      current.includes(placeId) ? current.filter((id) => id !== placeId) : [...current, placeId],
    );
  }, []);

  const stageMessage =
    phase === "running" || phase === "submitting"
      ? stage
        ? STAGE_COPY[stage]
        : waking
          ? "Waking up the AI planner…"
          : "Starting the planner…"
      : null;

  const value = useMemo(
    () => ({
      readOnly,
      planId,
      result,
      phase,
      progress,
      stage,
      stageMessage,
      errorMessage,
      recoverable,
      creditRefunded,
      selectedDayIndex,
      setSelectedDayIndex,
      showFullTrip,
      setShowFullTrip,
      selectedPlaceId,
      setSelectedPlaceId,
      lockedStopIds,
      skipStopIds,
      toggleLock,
      toggleSkip,
      generate,
      regenerate,
      loadPlan,
    }),
    [
      creditRefunded,
      errorMessage,
      generate,
      loadPlan,
      lockedStopIds,
      phase,
      planId,
      progress,
      readOnly,
      recoverable,
      regenerate,
      result,
      selectedDayIndex,
      selectedPlaceId,
      showFullTrip,
      skipStopIds,
      stage,
      stageMessage,
      toggleLock,
      toggleSkip,
    ],
  );

  return <PlanSessionContext.Provider value={value}>{children}</PlanSessionContext.Provider>;
}

export function usePlanSession() {
  const value = useContext(PlanSessionContext);
  if (!value) {
    throw new Error("usePlanSession must be used within PlanSessionProvider");
  }
  return value;
}

export function usePlanSessionOptional() {
  return useContext(PlanSessionContext);
}
