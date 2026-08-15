import {
  PATH_PLAN,
  PATH_PLAN_GET,
  PATH_PLAN_STATUS,
  PATH_REGENERATE,
  PlanAcceptedSchema,
  PlanErrorSchema,
  PlanResultSchema,
  PlanStatusSchema,
  type PlanAccepted,
  type PlanError,
  type PlanRequest,
  type PlanResult,
  type PlanStatus,
  type RegenerateRequest,
} from "@cuvoy/contracts";

import { fetchBackend, getFastApiUrl } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";

export { ApiTimeoutError, fetchBackend, getFastApiUrl, pingHealth } from "@/lib/api";

export class PlanApiError extends Error {
  readonly status: number;
  readonly body: PlanError | null;

  constructor(message: string, status: number, body: PlanError | null) {
    super(message);
    this.name = "PlanApiError";
    this.status = status;
    this.body = body;
  }
}

function withId(template: string, planId: string): string {
  return template.replace("{id}", encodeURIComponent(planId));
}

async function readPlanError(response: Response): Promise<PlanError | null> {
  try {
    return PlanErrorSchema.parse(await response.json());
  } catch {
    return null;
  }
}

async function withAuth(headers?: HeadersInit): Promise<Headers> {
  const next = new Headers(headers);
  const token = await getAccessToken();
  if (token) {
    next.set("Authorization", `Bearer ${token}`);
  }
  return next;
}

async function throwIfNotOk(response: Response): Promise<void> {
  if (response.ok) {
    return;
  }
  const body = await readPlanError(response);
  throw new PlanApiError(
    body?.message || `Request failed (${response.status})`,
    response.status,
    body,
  );
}

export async function createPlan(
  body: PlanRequest,
  timeoutMs: number,
  idempotencyKey: string,
): Promise<PlanAccepted> {
  const response = await fetchBackend(PATH_PLAN, {
    method: "POST",
    headers: await withAuth({
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    }),
    body: JSON.stringify(body),
    timeoutMs,
  });
  await throwIfNotOk(response);
  return PlanAcceptedSchema.parse(await response.json());
}

export async function getPlan(planId: string, timeoutMs: number): Promise<PlanResult> {
  const response = await fetchBackend(withId(PATH_PLAN_GET, planId), {
    method: "GET",
    headers: await withAuth(),
    cache: "no-store",
    timeoutMs,
  });
  if (response.status === 409) {
    throw new PlanApiError("Plan is still running", 409, null);
  }
  await throwIfNotOk(response);
  return PlanResultSchema.parse(await response.json());
}

export async function getPlanStatus(planId: string, timeoutMs: number): Promise<PlanStatus> {
  const response = await fetchBackend(withId(PATH_PLAN_STATUS, planId), {
    method: "GET",
    headers: await withAuth({ Accept: "application/json" }),
    cache: "no-store",
    timeoutMs,
  });
  await throwIfNotOk(response);
  return PlanStatusSchema.parse(await response.json());
}

export async function regeneratePlan(
  planId: string,
  body: RegenerateRequest,
  timeoutMs: number,
): Promise<PlanAccepted> {
  const response = await fetchBackend(withId(PATH_REGENERATE, planId), {
    method: "POST",
    headers: await withAuth({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
    timeoutMs,
  });
  await throwIfNotOk(response);
  return PlanAcceptedSchema.parse(await response.json());
}

export function planStatusStreamUrl(planId: string): string {
  return `${getFastApiUrl()}${withId(PATH_PLAN_STATUS, planId)}?stream=1`;
}
