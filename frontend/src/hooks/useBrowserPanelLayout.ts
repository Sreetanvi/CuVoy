"use client";

import { useCallback, useEffect, useState } from "react";
import type { Layout } from "react-resizable-panels";

function storageKey(id: string): string {
  return `cuvoy-panel-layout:${id}`;
}

export function useBrowserPanelLayout(id: string) {
  const [defaultLayout, setDefaultLayout] = useState<Layout | undefined>(undefined);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      const raw = window.localStorage.getItem(storageKey(id));
      if (raw) {
        setDefaultLayout(JSON.parse(raw) as Layout);
      }
    } catch {
      /* private mode or invalid JSON */
    }
    setReady(true);
  }, [id]);

  const onLayoutChanged = useCallback((layout: Layout) => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      window.localStorage.setItem(storageKey(id), JSON.stringify(layout));
    } catch {
      /* quota or private mode */
    }
    window.dispatchEvent(new Event("cuvoy-panel-layout"));
  }, [id]);

  return { defaultLayout, onLayoutChanged, ready };
}
