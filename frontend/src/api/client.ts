const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8080/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Token lives in memory only (module-level variable), never in
// localStorage/sessionStorage. The full blueprint calls for httpOnly
// cookies, which would require auth-service to issue Set-Cookie -- out of
// scope this pass (see SECURITY.md). In-memory-only is strictly more XSS-
// resistant than localStorage, at the cost of losing the session on a full
// page reload.
let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  isFormData?: boolean;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    if (options.isFormData) {
      body = options.body as FormData;
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.body);
    }
  }

  const resp = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
  });

  if (!resp.ok) {
    let message = resp.statusText;
    try {
      const data = await resp.json();
      if (typeof data.detail === "string") {
        message = data.detail;
      }
    } catch {
      // response wasn't JSON; fall back to statusText
    }
    throw new ApiError(resp.status, message);
  }

  if (resp.status === 204) {
    return undefined as T;
  }
  return (await resp.json()) as T;
}
