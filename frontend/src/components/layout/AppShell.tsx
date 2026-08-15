"use client";

import { AI_DISCLAIMER } from "@cuvoy/contracts";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Group, Panel } from "react-resizable-panels";

import { Header } from "@/components/layout/Header";
import { ResizeHandle } from "@/components/layout/ResizeHandle";
import { ColdStartBanner } from "@/components/planner/ColdStartBanner";
import { InputBar } from "@/components/planner/InputBar";
import { ItineraryPanel } from "@/components/planner/ItineraryPanel";
import { MapPanel } from "@/components/planner/MapPanel";
import { PanelErrorBoundary } from "@/components/planner/PanelErrorBoundary";
import { ProgressSSE } from "@/components/planner/ProgressSSE";
import { TripControls } from "@/components/planner/TripControls";
import { useBrowserPanelLayout } from "@/hooks/useBrowserPanelLayout";
import { cn } from "@/lib/utils";

type MobileTab = "itinerary" | "map";

function MapItinerarySplit({
  desktop,
  mobileTab,
  setMobileTab,
}: {
  desktop: boolean;
  mobileTab: MobileTab;
  setMobileTab: (tab: MobileTab) => void;
}) {
  const { defaultLayout, onLayoutChanged, ready } = useBrowserPanelLayout(
    "cuvoy-map-itinerary",
  );

  if (!ready) {
    return <div className="h-full min-h-0 w-full" />;
  }

  if (!desktop) {
    return (
      <div className="flex h-full min-h-0 flex-col">
        <div className="flex gap-1 border-b border-border px-3 py-2">
          <button
            type="button"
            className={cn(
              "flex-1 rounded-md px-3 py-1.5 text-sm",
              mobileTab === "itinerary" ? "bg-muted font-medium" : "text-muted-foreground",
            )}
            onClick={() => setMobileTab("itinerary")}
          >
            Itinerary
          </button>
          <button
            type="button"
            className={cn(
              "flex-1 rounded-md px-3 py-1.5 text-sm",
              mobileTab === "map" ? "bg-muted font-medium" : "text-muted-foreground",
            )}
            onClick={() => setMobileTab("map")}
          >
            Map
          </button>
        </div>
        <div className={cn("h-full min-h-0 w-full flex-1", mobileTab === "map" ? "flex" : "hidden")}>
          <PanelErrorBoundary name="map">
            <MapPanel visible={mobileTab === "map"} />
          </PanelErrorBoundary>
        </div>
        <div className={cn("h-full min-h-0 w-full flex-1", mobileTab === "itinerary" ? "flex" : "hidden")}>
          <PanelErrorBoundary name="itinerary">
            <ItineraryPanel />
          </PanelErrorBoundary>
        </div>
      </div>
    );
  }

  return (
    <Group
      id="cuvoy-map-itinerary"
      orientation="horizontal"
      className="h-full min-h-0 w-full"
      defaultLayout={defaultLayout}
      onLayoutChanged={onLayoutChanged}
    >
      <Panel id="map" defaultSize="50" minSize={240} className="h-full min-h-0 min-w-0">
        <div className="h-full w-full">
          <PanelErrorBoundary name="map">
            <MapPanel visible />
          </PanelErrorBoundary>
        </div>
      </Panel>
      <ResizeHandle direction="horizontal" />
      <Panel id="itinerary" defaultSize="50" minSize={240} className="h-full min-h-0 min-w-0">
        <div className="h-full w-full">
          <PanelErrorBoundary name="itinerary">
            <ItineraryPanel />
          </PanelErrorBoundary>
        </div>
      </Panel>
    </Group>
  );
}

export function AppShell({
  readOnly = false,
  shareTitle,
}: {
  readOnly?: boolean;
  shareTitle?: string;
}) {
  const [mobileTab, setMobileTab] = useState<MobileTab>("itinerary");
  const [desktop, setDesktop] = useState(false);
  const { defaultLayout, onLayoutChanged, ready } = useBrowserPanelLayout(
    "cuvoy-planner-main",
  );

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)");
    const sync = () => setDesktop(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  const workspace = (
    <MapItinerarySplit desktop={desktop} mobileTab={mobileTab} setMobileTab={setMobileTab} />
  );

  return (
    <div className="flex h-dvh flex-col bg-background text-foreground">
      <Header />
      {readOnly ? (
        <p className="border-b border-border px-4 py-2 text-xs text-muted-foreground">
          Read-only shared trip{shareTitle ? ` · ${shareTitle}` : ""}. Recipients cannot regenerate.
        </p>
      ) : null}
      {readOnly ? null : <ColdStartBanner />}
      {readOnly ? null : <ProgressSSE />}
      {readOnly ? (
        <div className="min-h-0 flex-1">{workspace}</div>
      ) : !ready ? (
        <div className="min-h-0 flex-1" />
      ) : (
        <Group
          id="cuvoy-planner-main"
          orientation="vertical"
          className="min-h-0 w-full flex-1"
          defaultLayout={defaultLayout}
          onLayoutChanged={onLayoutChanged}
        >
          <Panel id="workspace" defaultSize="58" minSize={220} className="h-full min-h-0">
            <div className="h-full w-full">{workspace}</div>
          </Panel>
          <ResizeHandle direction="vertical" />
          <Panel id="controls" defaultSize="42" minSize={200} className="min-h-0 overflow-auto">
            <div className="flex h-full min-h-0 flex-col">
              <PanelErrorBoundary name="controls">
                <TripControls />
              </PanelErrorBoundary>
              <InputBar />
            </div>
          </Panel>
        </Group>
      )}
      <p
        className="border-t border-border px-4 py-2 text-[11px] text-muted-foreground"
        data-testid="ai-disclaimer-footer"
      >
        {AI_DISCLAIMER}{" "}
        <Link href="/disclaimer" className="underline-offset-4 hover:underline">
          Full disclaimer
        </Link>
      </p>
    </div>
  );
}
