import { clearPortalSession, hasPortalSession } from "./portal-session";
import type { ApiError } from "./types";
import { ApiRequestError } from "./api-client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const PORTAL_AUTH_ENDPOINTS = ["/api/v1/customer_portal/auth/login", "/api/v1/customer_portal/auth/refresh"];

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  searchParams?: Record<string, string | number | boolean | undefined>;
};

let refreshInFlight: Promise<boolean> | null = null;

/** Renews the portal access-token cookie. The refresh token itself is an
 * httpOnly cookie the browser sends automatically (Phase 18) -- this call
 * carries no body. */
async function refreshPortalSession(): Promise<boolean> {
  if (!hasPortalSession()) return false;

  const res = await fetch(`${API_BASE_URL}/api/v1/customer_portal/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  });
  if (!res.ok) {
    clearPortalSession();
    return false;
  }
  return true;
}

function getOrRefreshPortalSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = refreshPortalSession().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

function redirectToPortalLogin(): void {
  clearPortalSession();
  if (typeof window !== "undefined" && window.location.pathname !== "/portal/login") {
    window.location.href = "/portal/login";
  }
}

/** Authentication is carried by the httpOnly session cookie the browser
 * attaches automatically (`credentials: "include"`) -- no Authorization
 * header is set here (Phase 18). */
async function portalAuthFetch(url: string, init: { method?: string; headers?: Record<string, string>; body?: BodyInit }, path: string): Promise<Response> {
  const isAuthEndpoint = PORTAL_AUTH_ENDPOINTS.some((p) => path.startsWith(p));

  let response = await fetch(url, { ...init, credentials: "include" });

  if (response.status === 401 && !isAuthEndpoint) {
    const refreshed = await getOrRefreshPortalSession();
    if (refreshed) {
      response = await fetch(url, { ...init, credentials: "include" });
    }
  }

  if (response.status === 401 && !isAuthEndpoint) {
    redirectToPortalLogin();
  }

  return response;
}

export async function portalApiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (options.searchParams) {
    for (const [key, value] of Object.entries(options.searchParams)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }

  const response = await portalAuthFetch(
    url.toString(),
    {
      method: options.method ?? "GET",
      headers: { "Content-Type": "application/json" },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
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
