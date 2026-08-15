import type { PipelineStage } from "@cuvoy/contracts";

export const STAGE_COPY: Record<PipelineStage, string> = {
  extract: "Understanding preferences…",
  discover: "Finding places…",
  reduce: "Choosing the strongest stops…",
  cluster_matrix: "Mapping travel times…",
  optimize_schedule: "Ordering your days…",
  narrative_validate: "Writing the itinerary…",
};
