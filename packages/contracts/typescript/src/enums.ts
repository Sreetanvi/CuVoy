import { z } from "zod";

export const OwnedVehicleSchema = z.enum(["car", "bike", "camper", "bicycle"]);
export const PublicTransportModeSchema = z.enum([
  "walking",
  "metro",
  "taxi",
  "bus",
  "mixed",
]);
export const TransportModeSchema = z.enum([
  "walking",
  "metro",
  "taxi",
  "bus",
  "mixed",
  "car",
  "bike",
  "camper",
  "bicycle",
]);
export const MaxTransitPresetSchema = z.enum([
  "walkable",
  "relaxed",
  "balanced",
  "explorer",
  "no_limit",
  "custom",
]);
export const PaceSchema = z.enum(["relaxed", "moderate", "packed"]);
export const BudgetTierSchema = z.enum(["low", "mid", "high"]);
export const LocationTypeSchema = z.enum([
  "city",
  "state",
  "country",
  "region",
  "multi_city",
  "multi_country",
]);
export const CostLabelSchema = z.enum([
  "verified_fare",
  "estimated_cost",
  "unavailable",
]);
export const CrowdLevelSchema = z.enum([
  "very_quiet",
  "quiet",
  "moderate",
  "busy",
  "very_busy",
]);
export const CrowdConfidenceLevelSchema = z.enum(["high", "medium", "low"]);
export const WeatherSourceSchema = z.enum([
  "forecast",
  "historical_climate",
  "unavailable",
]);
export const WeatherConfidenceSchema = z.enum(["high", "moderate", "low", "none"]);
export const PlaceSourceSchema = z.enum([
  "mapbox",
  "osm",
  "opentripmap",
  "geonames",
  "wikipedia",
  "official",
]);
export const GroupPrioritySchema = z.enum(["everyone", "team_lead"]);
export const ItineraryItemTypeSchema = z.enum([
  "activity",
  "meal",
  "transit",
  "break",
  "travel_day",
]);
export const WarningCodeSchema = z.enum([
  "closes_before_arrival",
  "reservation_likely",
  "hours_unverified",
  "cost_unavailable",
]);
export const JobStatusSchema = z.enum([
  "queued",
  "running",
  "resumable",
  "complete",
  "failed",
]);
export const PipelineStageSchema = z.enum([
  "extract",
  "discover",
  "reduce",
  "cluster_matrix",
  "optimize_schedule",
  "narrative_validate",
]);
export const SseEventTypeSchema = z.enum([
  "stage_start",
  "stage_complete",
  "plan_complete",
  "plan_error",
]);
export const HealthStateSchema = z.enum(["ok", "degraded", "unavailable"]);

export type OwnedVehicle = z.infer<typeof OwnedVehicleSchema>;
export type PublicTransportMode = z.infer<typeof PublicTransportModeSchema>;
export type TransportMode = z.infer<typeof TransportModeSchema>;
export type MaxTransitPreset = z.infer<typeof MaxTransitPresetSchema>;
export type Pace = z.infer<typeof PaceSchema>;
export type BudgetTier = z.infer<typeof BudgetTierSchema>;
export type LocationType = z.infer<typeof LocationTypeSchema>;
export type CostLabel = z.infer<typeof CostLabelSchema>;
export type CrowdLevel = z.infer<typeof CrowdLevelSchema>;
export type CrowdConfidenceLevel = z.infer<typeof CrowdConfidenceLevelSchema>;
export type WeatherSource = z.infer<typeof WeatherSourceSchema>;
export type WeatherConfidence = z.infer<typeof WeatherConfidenceSchema>;
export type PlaceSource = z.infer<typeof PlaceSourceSchema>;
export type GroupPriority = z.infer<typeof GroupPrioritySchema>;
export type ItineraryItemType = z.infer<typeof ItineraryItemTypeSchema>;
export type WarningCode = z.infer<typeof WarningCodeSchema>;
export type JobStatus = z.infer<typeof JobStatusSchema>;
export type PipelineStage = z.infer<typeof PipelineStageSchema>;
export type SseEventType = z.infer<typeof SseEventTypeSchema>;
export type HealthState = z.infer<typeof HealthStateSchema>;
