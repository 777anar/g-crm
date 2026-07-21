import {
  clearPortalTokens,
  getPortalAccessToken,
  getPortalRefreshToken,
  setPortalAccessToken,
} from "./portal-session";
import type { ApiError } from "./types";
import { ApiRequestError } from "./api-client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const PORTAL_AUTH_ENDPOINTS = ["/api/v1/customer_portal/auth/login", "/api/v1/customer_portal/auth/refresh"];

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  searchParams?: Record<string, string | number | boolean | undefined>;
};

let refreshInFlight: Promise<string | null> | null = null;

async function refreshPortalSession(): Promise<string | null> {
  const refreshToken = getPortalRefreshToken();
  if (!refreshToken) return null;

  const res = await fetch(`${API_BASE_URL}/api/v1/customer_portal/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) return null;
  try {
    const { access_token: freshToken } = (await res.json()) as { access_token: string };
    setPortalAccessToken(freshToken);
    return freshToken;
  } catch {
    return null;
  }
}

function getOrRefreshPortalSession(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = refreshPortalSession().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

function redirectToPortalLogin(): void {
  clearPortalTokens();
  if (typeof window !== "undefined" && window.location.pathname !== "/portal/login") {
    window.location.href = "/portal/login";
  }
}

async function portalAuthFetch(url: string, init: { method?: string; headers?: Record<string, string>; body?: BodyInit }, path: string): Promise<Response> {
  const isAuthEndpoint = PORTAL_AUTH_ENDPOINTS.some((p) => path.startsWith(p));
  const token = getPortalAccessToken();
  const headers: Record<string, string> = { ...init.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let response = await fetch(url, { ...init, headers });

  if (response.status === 401 && !isAuthEndpoint) {
    const newToken = await getOrRefreshPortalSession();
    if (newToken) {
      const retryHeaders: Record<string, string> = { ...init.headers, Authorization: `Bearer ${newToken}` };
      response = await fetch(url, { ...init, headers: retryHeaders });
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
