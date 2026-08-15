"use client";

import { createContext, useContext } from "react";

import { useColdStart } from "@/hooks/useColdStart";

type ColdStartContextValue = ReturnType<typeof useColdStart>;

const ColdStartContext = createContext<ColdStartContextValue | null>(null);

export function ColdStartProvider({ children }: { children: React.ReactNode }) {
  const value = useColdStart();
  return <ColdStartContext.Provider value={value}>{children}</ColdStartContext.Provider>;
}

export function useColdStartContext() {
  const value = useContext(ColdStartContext);
  if (!value) {
    throw new Error("useColdStartContext must be used within ColdStartProvider");
  }
  return value;
}
