import { getAccessToken } from "./session";
import type { ApiError } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiRequestError extends Error {
  code: string;
  details: { field: string; issue: string }[];
  status: number;
  requestId: string;

  constructor(status: number, body: ApiError) {
    super(body.error.message);
    this.code = body.error.code;
    this.details = body.error.details;
    this.status = status;
    this.requestId = body.error.request_id;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  formData?: FormData;
  searchParams?: Record<string, string | number | boolean | undefined>;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(path.startsWith("http") ? path : `${API_BASE_URL}${path}`);
  if (options.searchParams) {
    for (const [key, value] of Object.entries(options.searchParams)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }

  const token = getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!options.formData) headers["Content-Type"] = "application/json";

  const response = await fetch(url.toString(), {
    method: options.method ?? "GET",
    headers,
    body: options.formData ?? (options.body !== undefined ? JSON.stringify(options.body) : undefined),
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiError | null;
    if (body) throw new ApiRequestError(response.status, body);
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Downloads a binary response (PDF/Excel export) as a file. A plain
 * `<a href>` can't carry the Bearer token (it's stored in localStorage, not
 * a cookie -- see lib/session.ts), so exports must go through an
 * authenticated fetch and save the resulting blob client-side. */
export async function apiDownload(
  path: string,
  options: { searchParams?: Record<string, string | number | boolean | undefined>; filename: string }
): Promise<void> {
  const url = new URL(path.startsWith("http") ? path : `${API_BASE_URL}${path}`);
  if (options.searchParams) {
    for (const [key, value] of Object.entries(options.searchParams)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }

  const token = getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(url.toString(), { headers });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiError | null;
    if (body) throw new ApiRequestError(response.status, body);
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = options.filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}
