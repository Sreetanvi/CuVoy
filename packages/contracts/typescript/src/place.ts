import { z } from "zod";

import { PlaceSourceSchema } from "./enums";

export const PlaceSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  lat: z.number().gte(-90).lte(90),
  lng: z.number().gte(-180).lte(180),
  category: z.string().min(1),
  opening_hours: z.string().optional().nullable(),
  website: z.string().optional().nullable(),
  phone: z.string().optional().nullable(),
  address: z.string().optional().nullable(),
  source: PlaceSourceSchema,
});

export const ClusterSchema = z.object({
  id: z.string(),
  place_ids: z.array(z.string()),
  centroid_lat: z.number(),
  centroid_lng: z.number(),
  destination_id: z.string().optional().nullable(),
});

export type Place = z.infer<typeof PlaceSchema>;
export type Cluster = z.infer<typeof ClusterSchema>;
