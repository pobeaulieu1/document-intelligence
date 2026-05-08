import type { Extraction, LLMConfig, Schema, ValidationRule } from "./types";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Documents ─────────────────────────────────────────────────────────────

export async function listDocuments(schemaKey: string): Promise<Extraction[]> {
  return json(await fetch(`/schemas/${schemaKey}/documents`));
}

export async function uploadDocument(schemaKey: string, file: File): Promise<Extraction> {
  const form = new FormData();
  form.append("file", file);
  return json(await fetch(`/schemas/${schemaKey}/documents`, { method: "POST", body: form }));
}

export async function deleteDocument(schemaKey: string, docId: string): Promise<void> {
  const res = await fetch(`/schemas/${schemaKey}/documents/${docId}`, { method: "DELETE" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
}

export async function updateDocumentStatus(
  schemaKey: string,
  docId: string,
  status: "accepted" | "needs_review"
): Promise<Extraction> {
  return json(
    await fetch(`/schemas/${schemaKey}/documents/${docId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    })
  );
}

export function fileUrl(schemaKey: string, docId: string): string {
  return `/schemas/${schemaKey}/documents/${docId}/file`;
}

// ── Schema / Policy ───────────────────────────────────────────────────────

export async function getSchema(key: string): Promise<Schema> {
  return json(await fetch(`/schemas/${key}`));
}

export async function updateSchemaPolicy(
  key: string,
  rules: ValidationRule[]
): Promise<Schema> {
  return json(
    await fetch(`/schemas/${key}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rules }),
    })
  );
}

// ── Config ────────────────────────────────────────────────────────────────

export async function getLLMConfig(): Promise<LLMConfig> {
  return json(await fetch("/config/llm"));
}
