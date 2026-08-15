"use client";

import { Header } from "@/components/layout/Header";

export function PageFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh bg-background text-foreground">
      <Header />
      {children}
    </div>
  );
}
