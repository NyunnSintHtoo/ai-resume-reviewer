import type { ReviewListItem, ReviewStatusResponse } from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "resumate_token";
const ANON_KEY = "resumate_anon_id";

/** Per-browser anonymous identity: generated once, stored in localStorage,
 *  sent as X-Anon-Id on every request. No login needed to use the app. */
export function getAnonId(): string | null {
  if (typeof window === "undefined") return null;
  let id = localStorage.getItem(ANON_KEY);
  if (!id) {
    id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `anon-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
    localStorage.setItem(ANON_KEY, id);
  }
  return id;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const anonId = getAnonId();
  if (anonId) headers.set("X-Anon-Id", anonId);
  if (init.body && typeof init.body === "string") {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg)
        detail = body.detail[0].msg;
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------- auth
export async function register(email: string, password: string) {
  const body = await request<{ access_token: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(body.access_token);
}

export async function login(email: string, password: string) {
  const body = await request<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(body.access_token);
}

export function me() {
  return request<{ id: string; email: string }>("/auth/me");
}

// ---------------------------------------------------------------- reviews
export function submitReviewText(
  resumeText: string,
  jobDescription: string | null,
) {
  return request<ReviewStatusResponse>("/reviews", {
    method: "POST",
    body: JSON.stringify({
      resume_text: resumeText,
      job_description: jobDescription || null,
    }),
  });
}

export function submitReviewPdf(file: File, jobDescription: string | null) {
  const form = new FormData();
  form.append("file", file);
  if (jobDescription) form.append("job_description", jobDescription);
  return request<ReviewStatusResponse>("/reviews/upload", {
    method: "POST",
    body: form,
  });
}

export function getReview(id: string) {
  return request<ReviewStatusResponse>(`/reviews/${id}`);
}

export function getHistory() {
  return request<ReviewListItem[]>("/history");
}
