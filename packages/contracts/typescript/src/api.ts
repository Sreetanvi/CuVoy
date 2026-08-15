import { z } from "zod";

import {
  AlternativesSchema,
  ExplainabilitySchema,
  MapPayloadSchema,
  PackingListSchema,
  ProvenanceSchema,
  ValidationReportSchema,
} from "./enrichment";
import { HealthStateSchema, JobStatusSchema, PipelineStageSchema, SseEventTypeSchema } from "./enums";
import { ItinerarySchema, RouteLegSchema } from "./itinerary";
import { ExtractedPreferencesSchema, PlanRequestSchema, TripControlsSchema } from "./preferences";

export const HealthResponseSchema = z.object({
  status: HealthStateSchema,
  cache: HealthStateSchema,
  db: HealthStateSchema,
});

export const PlanAcceptedSchema = z.object({
  plan_id: z.string(),
  status: JobStatusSchema.default("queued"),
});

export const PlanStatusSchema = z.object({
  plan_id: z.string(),
  status: JobStatusSchema,
  stage: PipelineStageSchema.optional().nullable(),
  progress: z.number().int().min(0).max(100).default(0),
  resumable: z.boolean().default(false),
});

export const PlanResultSchema = z.object({
  plan_id: z.string(),
  timezone: z.string(),
  preferences: ExtractedPreferencesSchema,
  itinerary: ItinerarySchema,
  map: MapPayloadSchema,
  routes: z.array(RouteLegSchema).default([]),
  packing_list: PackingListSchema.optional().nullable(),
  explainability: ExplainabilitySchema.optional().nullable(),
  alternatives: AlternativesSchema.optional().nullable(),
  provenance: z.array(ProvenanceSchema).default([]),
  validation: ValidationReportSchema,
});

export const SwapRequestSchema = z.object({
  from_place_id: z.string(),
  to_place_id: z.string(),
});

export const MealOverrideSchema = z.object({
  day_index: z.number().int(),
  meal: z.string(),
  start_local: z.string().optional().nullable(),
  end_local: z.string().optional().nullable(),
  skip: z.boolean().default(false),
});

export const RegenerateRequestSchema = z.object({
  trip_controls: TripControlsSchema.optional().nullable(),
  skip_stop_ids: z.array(z.string()).default([]),
  locked_stop_ids: z.array(z.string()).default([]),
  swap: SwapRequestSchema.optional().nullable(),
  meal_override: MealOverrideSchema.optional().nullable(),
});

export const SseEventSchema = z.object({
  event: SseEventTypeSchema,
  stage: PipelineStageSchema.optional().nullable(),
  progress: z.number().int().min(0).max(100).optional().nullable(),
  plan_id: z.string().optional().nullable(),
  itinerary: ItinerarySchema.optional().nullable(),
  error: z.string().optional().nullable(),
  recoverable: z.boolean().optional().nullable(),
  credit_refunded: z.boolean().optional().nullable(),
});

export const PlanErrorSchema = z.object({
  error: z.string(),
  retryable: z.boolean(),
  credit_refunded: z.boolean(),
  message: z.string(),
});

export const SavedTripSchema = z.object({
  trip_id: z.string(),
  slug: z.string(),
  title: z.string(),
  plan_id: z.string().optional().nullable(),
  share_url: z.string().optional().nullable(),
});

export const SaveTripRequestSchema = z.object({
  plan_id: z.string(),
  title: z.string().optional().nullable(),
  user_id: z.string().min(1).optional().nullable(),
});

export const TripListSchema = z.object({
  trips: z.array(SavedTripSchema),
});

export const SharedTripSchema = z.object({
  trip: SavedTripSchema,
  result: PlanResultSchema,
  read_only: z.boolean().default(true),
});

export const AccountDeleteResponseSchema = z.object({
  deleted: z.boolean().default(true),
  trips_purged: z.number().int().default(0),
});

export const PdfStopLineSchema = z.object({
  start_local: z.string(),
  end_local: z.string(),
  title: z.string(),
  notes: z.string().optional().nullable(),
  cost: z.string().optional().nullable(),
  cost_label: z.string().optional().nullable(),
});

export const PdfDayBlockSchema = z.object({
  day_index: z.number().int(),
  date: z.string(),
  timezone: z.string(),
  timezone_abbrev: z.string(),
  city: z.string().optional().nullable(),
  stops: z.array(PdfStopLineSchema).default([]),
  daily_total: z.string().optional().nullable(),
});

export const PdfRouteLabelSchema = z.object({
  from_place_id: z.string(),
  to_place_id: z.string(),
  duration_label: z.string(),
  distance_label: z.string().optional().nullable(),
});

export const PdfExportResponseSchema = z.object({
  plan_id: z.string(),
  renderer: z.literal("client").default("client"),
  title: z.string(),
  logo_placement: z.literal("corner").default("corner"),
  disclaimer: z.string(),
  timezone: z.string(),
  days: z.array(PdfDayBlockSchema).default([]),
  route_labels: z.array(PdfRouteLabelSchema).default([]),
  map_hint: z.string(),
});

export const PlanCreateRequestSchema = PlanRequestSchema;

export type HealthResponse = z.infer<typeof HealthResponseSchema>;
export type PlanAccepted = z.infer<typeof PlanAcceptedSchema>;
export type PlanStatus = z.infer<typeof PlanStatusSchema>;
export type PlanResult = z.infer<typeof PlanResultSchema>;
export type RegenerateRequest = z.infer<typeof RegenerateRequestSchema>;
export type SseEvent = z.infer<typeof SseEventSchema>;
export type PlanError = z.infer<typeof PlanErrorSchema>;
export type SavedTrip = z.infer<typeof SavedTripSchema>;
export type SaveTripRequest = z.infer<typeof SaveTripRequestSchema>;
export type TripList = z.infer<typeof TripListSchema>;
export type SharedTrip = z.infer<typeof SharedTripSchema>;
export type AccountDeleteResponse = z.infer<typeof AccountDeleteResponseSchema>;
export type PdfStopLine = z.infer<typeof PdfStopLineSchema>;
export type PdfDayBlock = z.infer<typeof PdfDayBlockSchema>;
export type PdfRouteLabel = z.infer<typeof PdfRouteLabelSchema>;
export type PdfExportResponse = z.infer<typeof PdfExportResponseSchema>;
