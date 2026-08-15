import { z } from "zod";

import { CostAmountSchema, LocalDateTimeSchema } from "./common";
import { CrowdConfidenceSchema, WeatherSchema } from "./enrichment";
import { ItineraryItemTypeSchema, TransportModeSchema, WarningCodeSchema } from "./enums";
import { PlaceSchema } from "./place";

export const ReservationInfoSchema = z.object({
  likely_needed: z.boolean(),
  website: z.string().optional().nullable(),
  phone: z.string().optional().nullable(),
  guidance: z.string(),
});

export const RouteLegSchema = z.object({
  from_place_id: z.string(),
  to_place_id: z.string(),
  duration_seconds: z.number().int(),
  duration_buffered_seconds: z.number().int(),
  distance_meters: z.number().int(),
  mode: TransportModeSchema,
  geometry: z.string().optional().nullable(),
  cost: CostAmountSchema.optional().nullable(),
});

export const ItineraryItemSchema = z.object({
  type: ItineraryItemTypeSchema,
  start: LocalDateTimeSchema,
  end: LocalDateTimeSchema,
  place: PlaceSchema.optional().nullable(),
  title: z.string().optional().nullable(),
  dwell_minutes: z.number().int().optional().nullable(),
  wait_minutes: z.number().int().optional().nullable(),
  travel_minutes: z.number().int().optional().nullable(),
  travel_minutes_buffered: z.number().int().optional().nullable(),
  cost: CostAmountSchema.optional().nullable(),
  crowd: CrowdConfidenceSchema.optional().nullable(),
  reason: z.string().optional().nullable(),
  warnings: z.array(WarningCodeSchema).default([]),
  reservation: ReservationInfoSchema.optional().nullable(),
  locked: z.boolean().default(false),
  route: RouteLegSchema.optional().nullable(),
});

export const DailyCostSchema = z.object({
  currency: z.string(),
  activities: CostAmountSchema.optional().nullable(),
  meals: CostAmountSchema.optional().nullable(),
  transport: CostAmountSchema.optional().nullable(),
  total_excluding_transport: z.number().optional().nullable(),
  total_including_transport: z.number().optional().nullable(),
  transport_shown: z.boolean().default(false),
});

export const ItineraryDaySchema = z.object({
  day_index: z.number().int(),
  date: z.string().date(),
  timezone: z.string(),
  city: z.string().optional().nullable(),
  is_travel_day: z.boolean().default(false),
  items: z.array(ItineraryItemSchema),
  daily_cost: DailyCostSchema.optional().nullable(),
  weather: WeatherSchema.optional().nullable(),
});

export const ItinerarySchema = z.object({
  days: z.array(ItineraryDaySchema),
  timezone: z.string(),
  currency: z.string(),
  narrative: z.string().optional().nullable(),
});

export type ReservationInfo = z.infer<typeof ReservationInfoSchema>;
export type RouteLeg = z.infer<typeof RouteLegSchema>;
export type ItineraryItem = z.infer<typeof ItineraryItemSchema>;
export type ItineraryDay = z.infer<typeof ItineraryDaySchema>;
export type Itinerary = z.infer<typeof ItinerarySchema>;
