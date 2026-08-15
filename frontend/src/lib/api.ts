import {
  COLD_START_CLIENT_TIMEOUT_MS,
  HealthResponseSchema,
  PATH_HEALTH,
  WARM_GENERATION_TIMEOUT_MS,
  type HealthResponse,
} from "@cuvoy/contracts";

export class ApiTimeoutError extends Error {
  constructor(message = "Request timed out") {
    super(message);
    this.name = "ApiTimeoutError";
  }
}

export function getFastApiUrl(): string {
  const raw = process.env.NEXT_PUBLIC_FASTAPI_URL?.trim();
  return (raw && raw.length > 0 ? raw : "http://localhost:8000").replace(/\/$/, "");
}

export async function fetchBackend(
  path: string,
  init: RequestInit & { timeoutMs?: number } = {},
): Promise<Response> {
  const { timeoutMs = WARM_GENERATION_TIMEOUT_MS, signal, ...rest } = init;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener("abort", () => controller.abort(), { once: true });
    }
  }

  try {
    return await fetch(`${getFastApiUrl()}${path}`, {
      ...rest,
      signal: controller.signal,
    });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ApiTimeoutError();
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export async function pingHealth(
  timeoutMs: number = COLD_START_CLIENT_TIMEOUT_MS,
): Promise<HealthResponse> {
  const response = await fetchBackend(PATH_HEALTH, {
    method: "GET",
    timeoutMs,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Health check failed (${response.status})`);
  }
  return HealthResponseSchema.parse(await response.json());
}

export { COLD_START_CLIENT_TIMEOUT_MS, WARM_GENERATION_TIMEOUT_MS };
