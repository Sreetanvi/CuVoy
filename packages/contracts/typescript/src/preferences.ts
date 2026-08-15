import { z } from "zod";

import {
  DEFAULT_DAY_END_LOCAL,
  DEFAULT_DAY_START_LOCAL,
  DEFAULT_DINNER_END,
  DEFAULT_DINNER_START,
  DEFAULT_LUNCH_END,
  DEFAULT_LUNCH_START,
  MEAL_MIN_DURATION_MINUTES,
} from "./constants";
import {
  BudgetTierSchema,
  GroupPrioritySchema,
  LocationTypeSchema,
  MaxTransitPresetSchema,
  OwnedVehicleSchema,
  PaceSchema,
  PublicTransportModeSchema,
} from "./enums";

export const BudgetInputSchema = z.object({
  daily_amount: z.number().positive(),
  currency: z.string().min(1),
  raw: z.string().optional().nullable(),
  tier: BudgetTierSchema.optional().nullable(),
});

export const TravelDatesSchema = z
  .object({
    start_date: z.string().date().optional().nullable(),
    end_date: z.string().date().optional().nullable(),
    duration_days: z.number().int().min(1).optional().nullable(),
  })
  .superRefine((value, ctx) => {
    const hasRange = Boolean(value.start_date && value.end_date);
    if (!hasRange && value.duration_days == null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Provide start_date+end_date or duration_days",
      });
    }
    if (hasRange && value.end_date! < value.start_date!) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "end_date must be on or after start_date",
      });
    }
  });

export const LocationInputSchema = z.object({
  query: z.string().min(1),
  type: LocationTypeSchema.optional().nullable(),
  radius_km: z.number().positive().optional().nullable(),
});

export const TransportationPreferenceSchema = z
  .object({
    owns_vehicle: z.boolean(),
    vehicle: OwnedVehicleSchema.optional().nullable(),
    public_mode: PublicTransportModeSchema.optional().nullable(),
  })
  .superRefine((value, ctx) => {
    if (value.owns_vehicle && !value.vehicle) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "vehicle is required when owns_vehicle is true",
      });
    }
  })
  .transform((value) => {
    if (!value.owns_vehicle && value.public_mode == null) {
      return { ...value, public_mode: "mixed" as const };
    }
    return value;
  });

export const TravelerSchema = z.object({
  name: z.string().optional().nullable(),
  interests: z.array(z.string()).default([]),
  is_team_lead: z.boolean().default(false),
});

export const GroupPlanningSchema = z.object({
  enabled: z.boolean().default(false),
  travelers: z.array(TravelerSchema).default([]),
  priority: GroupPrioritySchema.default("everyone"),
});

export const AccessibilityPreferencesSchema = z.object({
  kids: z.boolean().default(false),
  elderly: z.boolean().default(false),
  wheelchair: z.boolean().default(false),
  notes: z.string().optional().nullable(),
});

export const FoodPreferencesSchema = z.object({
  dietary_restrictions: z.array(z.string()).default([]),
  cuisines: z.array(z.string()).default([]),
});

export const MealWindowSchema = z.object({
  start_local: z.string(),
  end_local: z.string(),
  min_duration_minutes: z.number().int().min(60).default(MEAL_MIN_DURATION_MINUTES),
});

export const TripControlsSchema = z
  .object({
    max_transit_preset: MaxTransitPresetSchema.default("balanced"),
    max_transit_minutes: z.number().int().min(1).optional().nullable(),
    pace: PaceSchema.default("moderate"),
    day_start_local: z.string().default(DEFAULT_DAY_START_LOCAL),
    day_end_local: z.string().default(DEFAULT_DAY_END_LOCAL),
    lunch: MealWindowSchema.default({
      start_local: DEFAULT_LUNCH_START,
      end_local: DEFAULT_LUNCH_END,
      min_duration_minutes: MEAL_MIN_DURATION_MINUTES,
    }),
    dinner: MealWindowSchema.default({
      start_local: DEFAULT_DINNER_START,
      end_local: DEFAULT_DINNER_END,
      min_duration_minutes: MEAL_MIN_DURATION_MINUTES,
    }),
    transportation: TransportationPreferenceSchema.optional().nullable(),
    daily_budget: BudgetInputSchema.optional().nullable(),
    hidden_gems: z.boolean().default(false),
    group: GroupPlanningSchema.default({
      enabled: false,
      travelers: [],
      priority: "everyone",
    }),
    show_transport_cost: z.boolean().default(false),
    accessibility: AccessibilityPreferencesSchema.default({
      kids: false,
      elderly: false,
      wheelchair: false,
      notes: null,
    }),
  })
  .superRefine((value, ctx) => {
    if (value.max_transit_preset === "custom" && value.max_transit_minutes == null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "max_transit_minutes required when preset is custom",
      });
    }
  });

export const PlanRequestSchema = z.object({
  user_prompt: z.string().min(1),
  budget: BudgetInputSchema.optional().nullable(),
  transportation: TransportationPreferenceSchema.optional().nullable(),
  travel_dates: TravelDatesSchema,
  location: LocationInputSchema,
  trip_controls: TripControlsSchema.optional().nullable(),
});

export const ExtractedPreferencesSchema = z.object({
  budget: BudgetInputSchema.optional().nullable(),
  dates: TravelDatesSchema.optional().nullable(),
  interests: z.array(z.string()).default([]),
  pace: PaceSchema.default("moderate"),
  food: FoodPreferencesSchema.default({
    dietary_restrictions: [],
    cuisines: [],
  }),
  hidden_gems: z.boolean().default(false),
  accessibility: AccessibilityPreferencesSchema.default({
    kids: false,
    elderly: false,
    wheelchair: false,
    notes: null,
  }),
  group: GroupPlanningSchema.default({
    enabled: false,
    travelers: [],
    priority: "everyone",
  }),
  transportation: TransportationPreferenceSchema.optional().nullable(),
  timezone: z.string().optional().nullable(),
});

export type BudgetInput = z.infer<typeof BudgetInputSchema>;
export type TravelDates = z.infer<typeof TravelDatesSchema>;
export type LocationInput = z.infer<typeof LocationInputSchema>;
export type TransportationPreference = z.infer<typeof TransportationPreferenceSchema>;
export type TripControls = z.infer<typeof TripControlsSchema>;
export type PlanRequest = z.infer<typeof PlanRequestSchema>;
export type ExtractedPreferences = z.infer<typeof ExtractedPreferencesSchema>;
