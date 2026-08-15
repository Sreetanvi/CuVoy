"use client";

import "mapbox-gl/dist/mapbox-gl.css";

import mapboxgl from "mapbox-gl";
import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";

import { usePlanSession } from "@/context/PlanSessionContext";
import { formatBufferedTravel } from "@/lib/format";
import { isValidLngLat } from "@/lib/geo";
import { getMapboxToken } from "@/lib/mapbox";
import {
  DEFAULT_ROUTE_COLOR,
  dayRouteColor,
  escapeHtml,
  routeFeaturesFromStops,
  visibleDays,
  visitStopsForDays,
} from "@/lib/mapStops";

const ROUTE_SOURCE = "cuvoy-routes";
const ROUTE_LAYER = "cuvoy-routes-line";
const LINE_COLOR: mapboxgl.ExpressionSpecification = [
  "coalesce",
  ["get", "color"],
  DEFAULT_ROUTE_COLOR,
];

const PANEL_LAYOUT_EVENT = "cuvoy-panel-layout";

type Props = { visible: boolean };

export function MapCanvas({ visible }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);
  const { resolvedTheme } = useTheme();
  const { result, selectedDayIndex, showFullTrip, selectedPlaceId, setSelectedPlaceId } =
    usePlanSession();
  const token = getMapboxToken();

  useEffect(() => {
    if (!token || !containerRef.current || mapRef.current) {
      return;
    }
    mapboxgl.accessToken = token;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: resolvedTheme === "dark" ? "mapbox://styles/mapbox/dark-v11" : "mapbox://styles/mapbox/light-v11",
      center: [77.5946, 12.9716],
      zoom: 3,
      attributionControl: true,
    });
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");
    const onLoad = () => {
      map.resize();
    };
    map.on("load", onLoad);
    mapRef.current = map;
    return () => {
      map.off("load", onLoad);
      markersRef.current.forEach((pin) => pin.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
    };
    // Theme is applied at creation; remount if the token appears.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    const map = mapRef.current;
    const node = containerRef.current;
    if (!map || !node) {
      return;
    }

    const resize = () => {
      if (!visible) {
        return;
      }
      requestAnimationFrame(() => {
        if (map && typeof map.getCanvas === "function" && map.getCanvas()) {
          map.resize();
        }
      });
    };

    const observer = new ResizeObserver(resize);
    observer.observe(node);
    if (node.parentElement) {
      observer.observe(node.parentElement);
    }
    window.addEventListener("resize", resize);
    window.addEventListener(PANEL_LAYOUT_EVENT, resize);
    resize();
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener(PANEL_LAYOUT_EVENT, resize);
    };
  }, [visible]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !result) {
      return;
    }

    const draw = () => {
      map.resize();
      const days = visibleDays(result, selectedDayIndex, showFullTrip);
      const stops = visitStopsForDays(days, { continuous: showFullTrip });
      const collection = {
        type: "FeatureCollection" as const,
        features: routeFeaturesFromStops(stops, days),
      };

      if (map.getSource(ROUTE_SOURCE)) {
        (map.getSource(ROUTE_SOURCE) as mapboxgl.GeoJSONSource).setData(collection);
        if (map.getLayer(ROUTE_LAYER)) {
          map.setPaintProperty(ROUTE_LAYER, "line-color", LINE_COLOR);
          map.setFilter(ROUTE_LAYER, null);
        }
      } else if (map.isStyleLoaded()) {
        map.addSource(ROUTE_SOURCE, {
          type: "geojson",
          data: collection,
        });
        map.addLayer({
          id: ROUTE_LAYER,
          type: "line",
          source: ROUTE_SOURCE,
          paint: {
            "line-color": LINE_COLOR,
            "line-width": 4,
          },
        });
      }

      markersRef.current.forEach((pin) => pin.remove());
      markersRef.current = [];

      stops.forEach((stop) => {
        const selected = stop.placeId === selectedPlaceId;
        const el = document.createElement("button");
        el.type = "button";
        el.className = "cuvoy-marker";
        el.textContent = String(stop.sequence);
        el.style.width = "24px";
        el.style.height = "24px";
        el.style.borderRadius = "999px";
        el.style.border = selected ? "2px solid #ffffff" : "2px solid #ffffff";
        el.style.background = selected ? "#111111" : dayRouteColor(stop.dayIndex);
        el.style.color = "#ffffff";
        el.style.fontSize = "11px";
        el.style.fontWeight = "700";
        el.style.lineHeight = "20px";
        el.style.textAlign = "center";
        el.style.padding = "0";
        el.style.cursor = "pointer";
        el.setAttribute("aria-label", `${stop.sequence}. ${stop.name}`);
        const travel = formatBufferedTravel(stop.item.route?.duration_buffered_seconds);
        const html = `
          <div style="max-width:220px;font-size:12px">
            <strong>${escapeHtml(stop.name)}</strong>
            <p>Arrival ${escapeHtml(stop.arrival)}</p>
            <p>Duration ${escapeHtml(stop.duration)}</p>
            ${travel ? `<p>Travel ${escapeHtml(travel)}</p>` : ""}
          </div>
        `;
        const popup = new mapboxgl.Popup({ offset: 14, closeButton: false }).setHTML(html);
        const pin = new mapboxgl.Marker({ element: el })
          .setLngLat([stop.lng, stop.lat])
          .setPopup(popup)
          .addTo(map);
        markersRef.current.push(pin);
        const openPopup = () => {
          const popupInstance = pin.getPopup();
          if (popupInstance && !popupInstance.isOpen()) {
            pin.togglePopup();
          }
        };
        const closePopup = () => {
          const popupInstance = pin.getPopup();
          if (popupInstance?.isOpen()) {
            pin.togglePopup();
          }
        };
        el.addEventListener("mouseenter", openPopup);
        el.addEventListener("mouseleave", () => {
          if (stop.placeId !== selectedPlaceId) {
            closePopup();
          }
        });
        el.addEventListener("click", () => {
          setSelectedPlaceId(stop.placeId);
          openPopup();
        });
        if (selected) {
          openPopup();
        }
      });

      const selected = stops.find((stop) => stop.placeId === selectedPlaceId);
      try {
        if (selected && isValidLngLat(selected.lng, selected.lat)) {
          map.easeTo({ center: [selected.lng, selected.lat], zoom: Math.max(map.getZoom(), 12) });
        } else if (stops.length > 1) {
          const bounds = new mapboxgl.LngLatBounds(
            [stops[0].lng, stops[0].lat],
            [stops[0].lng, stops[0].lat],
          );
          stops.forEach((stop) => bounds.extend([stop.lng, stop.lat]));
          map.fitBounds(bounds, { padding: 48, maxZoom: 13, duration: 600 });
        } else if (stops[0]) {
          map.easeTo({ center: [stops[0].lng, stops[0].lat], zoom: 12 });
        }
      } catch {
        if (stops[0]) {
          map.easeTo({ center: [stops[0].lng, stops[0].lat], zoom: 12 });
        }
      }
    };

    if (map.isStyleLoaded()) {
      draw();
      return undefined;
    }
    map.once("load", draw);
    return () => {
      map.off("load", draw);
    };
  }, [result, selectedDayIndex, selectedPlaceId, setSelectedPlaceId, showFullTrip]);

  if (!token) {
    return (
      <div className="flex h-full w-full items-center justify-center p-6 text-center text-sm text-muted-foreground">
        Add NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN to show the map.
      </div>
    );
  }

  return <div ref={containerRef} className="h-full min-h-0 w-full" />;
}
