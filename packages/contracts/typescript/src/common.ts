import { z } from "zod";

import { CostLabelSchema } from "./enums";

export const LocalDateTimeSchema = z.object({
  timezone: z.string().min(1),
  local_time: z.string().min(1),
  utc: z.string().datetime().optional().nullable(),
});

export const CostAmountSchema = z
  .object({
    amount: z.number().nullable(),
    currency: z.string().min(1),
    label: CostLabelSchema,
  })
  .superRefine((value, ctx) => {
    if (value.label === "unavailable" && value.amount !== null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Cost unavailable must not include an amount",
      });
    }
    if (value.label !== "unavailable" && value.amount === null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Verified or estimated cost requires an amount",
      });
    }
  });

export type LocalDateTime = z.infer<typeof LocalDateTimeSchema>;
export type CostAmount = z.infer<typeof CostAmountSchema>;
