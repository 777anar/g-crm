import { clearSession, getSessionClaims, hasSession, setSessionClaims } from "./session";
import type { ApiError } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Endpoints that are part of the auth flow itself: a 401 from these means
// "actually invalid," not "expired, please refresh" -- retrying them through
// the refresh flow would either loop or make no sense.
const AUTH_ENDPOINTS = ["/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/mfa/verify"];

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
let refreshInFlight: Promise<boolean> | null = null;

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

type ClaimsBody = {
  role?: string | null;
  module_permissions?: Record<string, string[]>;
  active_company_id?: string | null;
};

/** Renews the access-token cookie (Phase 18: the refresh token itself is an
 * httpOnly cookie the browser sends automatically -- this call carries no
 * body) and, if a company was previously selected, re-selects it (the
 * backend always issues an unscoped token from /auth/refresh, matching the
 * pre-Phase-18 behavior this mirrors). Returns whether the session is now
 * usable, since the caller can no longer receive a token value directly. */
async function refreshSession(): Promise<boolean> {
  if (!hasSession()) return false;

  const previousCompanyId = getSessionClaims()?.active_company_id ?? null;

  const res = await fetchWithOneRetry(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  });
  if (!res || !res.ok) {
    clearSession();
    return false;
  }
  let body: ClaimsBody;
  try {
    body = (await res.json()) as ClaimsBody;
  } catch {
    clearSession();
    return false;
  }
  setSessionClaims({
    role: body.role ?? null,
    module_permissions: body.module_permissions ?? {},
    active_company_id: body.active_company_id ?? null,
  });

  // /auth/refresh always issues a token with no active company; restore the
  // one the user had selected before it expired, so the retried request
  // (and everything after it) stays company-scoped. This sub-step is best
  // effort: if it fails (network error, backend hiccup), the base refresh
  // above already succeeded, so the session stays usable rather than being
  // discarded -- a request that then needs a company gets a normal "no
  // active company selected" response, not a spurious logout.
  if (previousCompanyId) {
    const selectRes = await fetchWithOneRetry(`${API_BASE_URL}/api/v1/auth/select-company`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ company_id: previousCompanyId }),
    });
    if (selectRes && selectRes.ok) {
      try {
        const selectBody = (await selectRes.json()) as ClaimsBody;
        setSessionClaims({
          role: selectBody.role ?? null,
          module_permissions: selectBody.module_permissions ?? {},
          active_company_id: selectBody.active_company_id ?? previousCompanyId,
        });
      } catch {
        // fall through -- the unscoped refresh above already succeeded
      }
    }
  }

  return true;
}

function getOrRefreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = refreshSession().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

function redirectToLogin(): void {
  clearSession();
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

/** Performs an authenticated fetch. Authentication itself is carried by the
 * httpOnly session cookie the browser attaches automatically (`credentials:
 * "include"`) -- no Authorization header is set here (Phase 18). On a 401,
 * transparently refreshes the session and retries once before giving up and
 * redirecting to /login. */
async function authFetch(url: string, init: { method?: string; headers?: Record<string, string>; body?: BodyInit }, path: string): Promise<Response> {
  const isAuthEndpoint = AUTH_ENDPOINTS.some((p) => path.startsWith(p));

  let response = await fetch(url, { ...init, credentials: "include" });

  if (response.status === 401 && !isAuthEndpoint) {
    const refreshed = await getOrRefreshSession();
    if (refreshed) {
      response = await fetch(url, { ...init, credentials: "include" });
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

/** Downloads a binary response (PDF/Excel export) as a file via an
 * authenticated fetch (the httpOnly session cookie rides along automatically),
 * saving the resulting blob client-side since a plain `<a href>` can't carry
 * cookie-scoped auth across origins the way this fetch call does. */
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
