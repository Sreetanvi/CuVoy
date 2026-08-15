import { z } from "zod";

import {
  CrowdConfidenceLevelSchema,
  CrowdLevelSchema,
  WeatherConfidenceSchema,
  WeatherSourceSchema,
} from "./enums";

export const WeatherSchema = z
  .object({
    source: WeatherSourceSchema,
    is_forecast: z.boolean(),
    confidence: WeatherConfidenceSchema,
    retrieved_at: z.string().datetime().optional().nullable(),
    climate_period: z.string().optional().nullable(),
    temperature_min: z.number().optional().nullable(),
    temperature_max: z.number().optional().nullable(),
    summary: z.string().optional().nullable(),
  })
  .superRefine((value, ctx) => {
    if (value.source === "forecast" && !value.is_forecast) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Live forecast must set is_forecast=true",
      });
    }
    if (value.source !== "forecast" && value.is_forecast) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Historical climate or unavailable must not be labeled forecast",
      });
    }
  });

export const CrowdConfidenceSchema = z.object({
  level: CrowdLevelSchema,
  confidence: CrowdConfidenceLevelSchema,
  reasons: z.array(z.string()).default([]),
});

export const PackingItemSchema = z.object({
  name: z.string(),
  reason: z.string(),
  category: z.string(),
});

export const PackingListSchema = z.object({
  items: z.array(PackingItemSchema),
  summary: z.string().optional().nullable(),
});

export const ExclusionReasonSchema = z.object({
  place_id: z.string().optional().nullable(),
  name: z.string(),
  reason: z.string(),
});

export const ExplainabilitySchema = z.object({
  exclusions: z.array(ExclusionReasonSchema).default([]),
});

export const AlternativePlaceSchema = z.object({
  place_id: z.string(),
  name: z.string(),
  reason: z.string(),
  swap_for_place_id: z.string().optional().nullable(),
});

export const AlternativesSchema = z.object({
  nearby_cities: z.array(z.string()).default([]),
  swap_suggestions: z.array(AlternativePlaceSchema).default([]),
});

export const ProvenanceSchema = z.object({
  field: z.string(),
  source: z.string(),
  retrieved_at: z.string().datetime().optional().nullable(),
  confidence: CrowdConfidenceLevelSchema.or(WeatherConfidenceSchema).optional().nullable(),
});

export const ValidationIssueSchema = z.object({
  code: z.string(),
  message: z.string(),
  path: z.string().optional().nullable(),
});

export const ValidationReportSchema = z.object({
  valid: z.boolean(),
  issues: z.array(ValidationIssueSchema).default([]),
});

export const MapMarkerSchema = z.object({
  place_id: z.string(),
  lat: z.number(),
  lng: z.number(),
  label: z.string(),
  day_index: z.number().int().optional().nullable(),
});

export const MapBoundsSchema = z.object({
  min_lat: z.number(),
  min_lng: z.number(),
  max_lat: z.number(),
  max_lng: z.number(),
});

export const MapPayloadSchema = z.object({
  markers: z.array(MapMarkerSchema),
  bounds: MapBoundsSchema.optional().nullable(),
});

export type Weather = z.infer<typeof WeatherSchema>;
export type CrowdConfidence = z.infer<typeof CrowdConfidenceSchema>;
export type PackingList = z.infer<typeof PackingListSchema>;
export type ExclusionReason = z.infer<typeof ExclusionReasonSchema>;
export type Explainability = z.infer<typeof ExplainabilitySchema>;
export type Alternatives = z.infer<typeof AlternativesSchema>;
export type Provenance = z.infer<typeof ProvenanceSchema>;
export type ValidationReport = z.infer<typeof ValidationReportSchema>;
export type MapPayload = z.infer<typeof MapPayloadSchema>;
