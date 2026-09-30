import type { CreateDigestRequest, CreateDigestResponse, DigestDetail, DigestSummary } from "./types";

const BASE = "/api";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json() as Promise<T>;
}

export function listDigests(limit?: number): Promise<{ digests: DigestSummary[] }> {
  const q = limit !== undefined ? `?limit=${limit}` : "";
  return getJson<{ digests: DigestSummary[] }>(`/digests${q}`);
}

export function getDigest(id: string): Promise<DigestDetail> {
  return getJson<DigestDetail>(`/digests/${encodeURIComponent(id)}`);
}

export async function createDigest(req: CreateDigestRequest): Promise<CreateDigestResponse> {
  const res = await fetch(`${BASE}/digests`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<CreateDigestResponse>;
}
