"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { AuthProvider } from "@/context/AuthContext";
import { ColdStartProvider } from "@/context/ColdStartContext";
import { ThemeProvider } from "@/context/ThemeProvider";
import { TripControlsProvider } from "@/context/TripControlsContext";
import { createQueryClient } from "@/lib/query";

export function AppProviders({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => createQueryClient());

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <TripControlsProvider>
            <ColdStartProvider>{children}</ColdStartProvider>
          </TripControlsProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
