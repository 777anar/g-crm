import { clearAccessToken, decodeActiveCompanyId, getAccessToken, getRefreshToken, setAccessToken } from "./session";
import type { ApiError } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Endpoints that are part of the auth flow itself: a 401 from these means
// "actually invalid," not "expired, please refresh" -- retrying them through
// the refresh flow would either loop or make no sense.
const AUTH_ENDPOINTS = ["/api/v1/auth/login", "/api/v1/auth/refresh"];

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

// Deduplicates concurrent refresh attempts: if several requests 401 at once
// (e.g. a page firing multiple fetches on load), they all await the same
// in-flight refresh instead of each hitting /auth/refresh separately.
let refreshInFlight: Promise<string | null> | null = null;

/** A token expiring mid-session on a data-heavy page (e.g. Dashboard) means
 * several requests can 401 within the same instant, all racing for the
 * browser's per-origin connection limit -- occasionally throwing a plain
 * "Failed to fetch" rather than resolving to a real HTTP response. One retry
 * after a short pause is enough for a connection slot to free up; this is
 * not meant to paper over a genuinely unreachable backend, just this one
 * common burst pattern. */
async function fetchWithOneRetry(url: string, init: RequestInit): Promise<Response | null> {
  try {
    return await fetch(url, init);
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 300));
    try {
      return await fetch(url, init);
    } catch {
      return null;
    }
  }
}

async function refreshSession(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  const expiredAccessToken = getAccessToken();
  const activeCompanyId = expiredAccessToken ? decodeActiveCompanyId(expiredAccessToken) : null;

  const res = await fetchWithOneRetry(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res || !res.ok) return null;
  let freshToken: string;
  try {
    ({ access_token: freshToken } = (await res.json()) as { access_token: string });
  } catch {
    return null;
  }

  // /auth/refresh always issues a token with no active company; restore the
  // one the user had selected before it expired, so the retried request
  // (and everything after it) stays company-scoped. This sub-step is best
  // effort: if it fails (network error, backend hiccup), the base refresh
  // above already succeeded, so fall back to the unscoped token rather than
  // discarding an otherwise-valid session -- a request that then needs a
  // company gets a normal "no active company selected" response, not a
  // spurious logout.
  if (activeCompanyId) {
    const selectRes = await fetchWithOneRetry(`${API_BASE_URL}/api/v1/auth/select-company`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${freshToken}` },
      body: JSON.stringify({ company_id: activeCompanyId }),
    });
    if (selectRes && selectRes.ok) {
      try {
        const { access_token: scopedToken } = (await selectRes.json()) as { access_token: string };
        setAccessToken(scopedToken);
        return scopedToken;
      } catch {
        // fall through to the unscoped token below
      }
    }
  }

  setAccessToken(freshToken);
  return freshToken;
}

function getOrRefreshSession(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = refreshSession().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

function redirectToLogin(): void {
  clearAccessToken();
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

/** Performs an authenticated fetch, transparently refreshing an expired
 * access token (via the stored refresh token) and retrying once on a 401
 * before giving up and redirecting to /login. */
async function authFetch(url: string, init: { method?: string; headers?: Record<string, string>; body?: BodyInit }, path: string): Promise<Response> {
  const isAuthEndpoint = AUTH_ENDPOINTS.some((p) => path.startsWith(p));
  const token = getAccessToken();
  const headers: Record<string, string> = { ...init.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let response = await fetch(url, { ...init, headers });

  if (response.status === 401 && !isAuthEndpoint) {
    const newToken = await getOrRefreshSession();
    if (newToken) {
      const retryHeaders: Record<string, string> = { ...init.headers, Authorization: `Bearer ${newToken}` };
      response = await fetch(url, { ...init, headers: retryHeaders });
    }
  }

  if (response.status === 401 && !isAuthEndpoint) {
    redirectToLogin();
  }

  return response;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(path.startsWith("http") ? path : `${API_BASE_URL}${path}`);
  if (options.searchParams) {
    for (const [key, value] of Object.entries(options.searchParams)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }

  const headers: Record<string, string> = {};
  if (!options.formData) headers["Content-Type"] = "application/json";

  const response = await authFetch(
    url.toString(),
    {
      method: options.method ?? "GET",
      headers,
      body: options.formData ?? (options.body !== undefined ? JSON.stringify(options.body) : undefined),
    },
    path
  );

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

  const response = await authFetch(url.toString(), {}, path);
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
