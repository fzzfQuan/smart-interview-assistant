import type { LoginRequest, RegisterRequest, TokenResponse, User } from "../types/auth";

const API_BASE = "/api/v1";

function authHeaders(token: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/* ── 认证 ── */

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const resp = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `登录失败 (${resp.status})`);
  }
  return resp.json();
}

export async function register(data: RegisterRequest): Promise<TokenResponse> {
  const resp = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `注册失败 (${resp.status})`);
  }
  return resp.json();
}

export async function getMe(token: string): Promise<User> {
  const resp = await fetch(`${API_BASE}/auth/me`, {
    headers: authHeaders(token),
  });
  if (!resp.ok) {
    throw new Error("登录已过期，请重新登录");
  }
  return resp.json();
}

/* ── 简历上传（SSE 流式） ── */

export async function uploadResumeStream(
  file: File,
  jobDescription: string,
  token: string | null,
  onProgress: (data: {
    stage: string;
    percentage: number;
    message: string;
  }) => void,
  onResult: (data: unknown) => void,
  onError: (message: string) => void,
  signal?: AbortSignal
): Promise<void> {
  const fd = new FormData();
  fd.append("file", file);
  if (jobDescription) fd.append("job_description", jobDescription);

  const resp = await fetch(`${API_BASE}/upload/stream`, {
    method: "POST",
    headers: authHeaders(token),
    body: fd,
    signal,
  });

  if (!resp.ok) {
    const errBody = await resp.json().catch(() => ({}));
    throw new Error(errBody.detail || `请求失败 (${resp.status})`);
  }

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventType = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7);
      } else if (line.startsWith("data: ")) {
        const data = JSON.parse(line.slice(6));
        switch (eventType) {
          case "progress":
            onProgress(data);
            break;
          case "result":
            onResult(data);
            break;
          case "error":
            onError(data.message);
            throw new Error(data.message);
        }
        eventType = "";
      }
    }
  }
}
