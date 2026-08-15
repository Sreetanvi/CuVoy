"use client";

import {
  TripControlsSchema,
  type TripControls,
} from "@cuvoy/contracts";
import { createContext, useCallback, useContext, useMemo, useState } from "react";

export const DEFAULT_TRIP_CONTROLS: TripControls = TripControlsSchema.parse({});

type TripControlsContextValue = {
  controls: TripControls;
  setControls: (next: TripControls) => void;
  patchControls: (patch: Partial<TripControls>) => void;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
};

const TripControlsContext = createContext<TripControlsContextValue | null>(null);

export function TripControlsProvider({ children }: { children: React.ReactNode }) {
  const [controls, setControlsState] = useState<TripControls>(DEFAULT_TRIP_CONTROLS);
  const [collapsed, setCollapsed] = useState(false);

  const setControls = useCallback((next: TripControls) => {
    setControlsState(TripControlsSchema.parse(next));
  }, []);

  const patchControls = useCallback((patch: Partial<TripControls>) => {
    setControlsState((current) => TripControlsSchema.parse({ ...current, ...patch }));
  }, []);

  const value = useMemo(
    () => ({ controls, setControls, patchControls, collapsed, setCollapsed }),
    [collapsed, controls, patchControls, setControls],
  );

  return (
    <TripControlsContext.Provider value={value}>{children}</TripControlsContext.Provider>
  );
}

export function useTripControls() {
  const value = useContext(TripControlsContext);
  if (!value) {
    throw new Error("useTripControls must be used within TripControlsProvider");
  }
  return value;
}
