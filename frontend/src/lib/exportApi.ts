import {
  AI_DISCLAIMER,
  ICS_FILENAME,
  PATH_EXPORT_ICS,
  PATH_EXPORT_PDF,
  PdfExportResponseSchema,
  type Itinerary,
  type PdfExportResponse,
  type PlanResult,
} from "@cuvoy/contracts";

import { fetchBackend } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import { clockPortion } from "@/lib/timezone";
import { downloadBlob, isValidIcs, itineraryToIcs } from "@/lib/ics";

function withId(template: string, planId: string): string {
  return template.replace("{id}", encodeURIComponent(planId));
}

async function authHeaders(extra?: HeadersInit): Promise<Headers> {
  const headers = new Headers(extra);
  const token = await getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

export async function downloadIcs(
  planId: string,
  timeoutMs: number,
  itinerary?: Itinerary | null,
): Promise<void> {
  let text = "";
  try {
    const response = await fetchBackend(withId(PATH_EXPORT_ICS, planId), {
      method: "GET",
      headers: await authHeaders({ Accept: "text/calendar" }),
      cache: "no-store",
      timeoutMs,
    });
    if (response.ok) {
      text = await response.text();
    }
  } catch {
    text = "";
  }
  if (!isValidIcs(text) && itinerary) {
    text = itineraryToIcs(itinerary, planId);
  }
  if (!isValidIcs(text)) {
    throw new Error("Calendar export failed");
  }
  downloadBlob(new Blob([text], { type: "text/calendar;charset=utf-8" }), ICS_FILENAME);
}

export function documentFromPlan(result: PlanResult): PdfExportResponse {
  const city = result.itinerary.days.find((day) => day.city)?.city;
  return {
    plan_id: result.plan_id,
    renderer: "client",
    title: city ? `Trip to ${city}` : "CuVoy itinerary",
    logo_placement: "corner",
    disclaimer: AI_DISCLAIMER,
    timezone: result.timezone || result.itinerary.timezone,
    days: result.itinerary.days.map((day) => ({
      day_index: day.day_index,
      date: day.date,
      timezone: day.timezone || result.itinerary.timezone,
      timezone_abbrev: day.timezone || result.itinerary.timezone,
      city: day.city ?? null,
      stops: day.items
        .filter((item) => item.type !== "transit" && item.type !== "break")
        .map((item) => ({
          start_local: clockPortion(item.start.local_time),
          end_local: clockPortion(item.end.local_time),
          title: item.title || item.place?.name || item.type,
          notes: item.reason ?? null,
          cost: item.cost?.amount != null ? `${item.cost.amount} ${item.cost.currency}` : null,
          cost_label: item.cost?.label ?? null,
        })),
      daily_total:
        day.daily_cost?.total_excluding_transport != null
          ? `${day.daily_cost.total_excluding_transport} ${day.daily_cost.currency}`
          : null,
    })),
    route_labels: [],
    map_hint: "Client itinerary export",
  };
}

export async function fetchPdfDocument(
  planId: string,
  timeoutMs: number,
): Promise<PdfExportResponse> {
  const response = await fetchBackend(withId(PATH_EXPORT_PDF, planId), {
    method: "GET",
    headers: await authHeaders(),
    cache: "no-store",
    timeoutMs,
  });
  if (!response.ok) {
    throw new Error(`PDF export failed (${response.status})`);
  }
  return PdfExportResponseSchema.parse(await response.json());
}

function pdfSafe(value: string): string {
  return value
    .replaceAll(/[^\u0020-\u007E]/g, "?")
    .replaceAll("\\", "\\\\")
    .replaceAll("(", "\\(")
    .replaceAll(")", "\\)");
}

export function buildSimplePdf(doc: PdfExportResponse): Blob {
  const lines = [
    doc.title,
    doc.disclaimer,
    ...doc.days.flatMap((day) => [
      `Day ${day.day_index + 1} ${day.date} ${day.timezone_abbrev}`,
      ...day.stops.map(
        (stop) =>
          `${stop.start_local}-${stop.end_local} ${stop.title}${stop.cost ? ` (${stop.cost})` : ""}`,
      ),
    ]),
  ].slice(0, 42);

  const encoder = new TextEncoder();
  const commands = lines
    .map((line, index) => `BT /F1 10 Tf 48 ${740 - index * 14} Td (${pdfSafe(line)}) Tj ET`)
    .join("\n");
  const stream = `${commands}\n`;
  const bodies = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    `<< /Length ${encoder.encode(stream).length} >>\nstream\n${stream}endstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];

  const chunks: Uint8Array[] = [encoder.encode("%PDF-1.4\n")];
  let offset = chunks[0].length;
  const offsets = [0];
  bodies.forEach((body, index) => {
    const object = encoder.encode(`${index + 1} 0 obj\n${body}\nendobj\n`);
    offsets.push(offset);
    chunks.push(object);
    offset += object.length;
  });
  const xrefLines = ["xref", `0 ${bodies.length + 1}`, "0000000000 65535 f "];
  for (let index = 1; index <= bodies.length; index += 1) {
    xrefLines.push(`${String(offsets[index]).padStart(10, "0")} 00000 n `);
  }
  chunks.push(encoder.encode(`${xrefLines.join("\n")}\n`));
  chunks.push(
    encoder.encode(
      `trailer << /Size ${bodies.length + 1} /Root 1 0 R >>\nstartxref\n${offset}\n%%EOF\n`,
    ),
  );
  const bytes = new Uint8Array(chunks.reduce((total, chunk) => total + chunk.length, 0));
  let cursor = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, cursor);
    cursor += chunk.length;
  }
  return new Blob([bytes], { type: "application/pdf" });
}

export async function downloadPdf(
  planId: string,
  timeoutMs: number,
  result?: PlanResult | null,
): Promise<void> {
  let doc: PdfExportResponse | null = result ? documentFromPlan(result) : null;
  try {
    doc = await fetchPdfDocument(planId, timeoutMs);
  } catch {
    if (!doc) {
      throw new Error("PDF export failed");
    }
  }
  downloadBlob(buildSimplePdf(doc), "cuvoy-trip.pdf");
}
