/**
 * Per-user identifier for the multi-user foundation (Wave 2.7).
 *
 * Generates and persists a UUID v4 in localStorage; this id is sent
 * as the `X-User-Id` header on every backend fetch. The backend
 * namespaces all storage under `data/users/{user_id}/` (ADR 0004).
 *
 * - MVP/self-hosted default: use "jingwen-default" in the browser too so
 *   seeded data remains visible after hydration.
 * - Set VITE_ENABLE_MULTI_USER=true to restore browser-generated UUIDs.
 * - The "rt:" prefix matches existing localStorage keys
 *   (e.g. rt:has-drafts, rt:sidebar-collapsed).
 */

const USER_ID_KEY = "rt:user_id";
const DEFAULT_USER_ID = "jingwen-default";

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

function multiUserEnabled(): boolean {
  const env = (typeof import.meta !== "undefined" ? import.meta.env : {}) as Record<
    string,
    string | boolean | undefined
  >;
  return env.VITE_ENABLE_MULTI_USER === true || env.VITE_ENABLE_MULTI_USER === "true";
}

function generateUuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // RFC4122 v4 fallback (covers older runtimes / SSR shims)
  const bytes = new Uint8Array(16);
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function getUserId(): string {
  if (!isBrowser()) return DEFAULT_USER_ID;
  if (!multiUserEnabled()) return DEFAULT_USER_ID;
  let id = localStorage.getItem(USER_ID_KEY);
  if (!id) {
    id = generateUuid();
    localStorage.setItem(USER_ID_KEY, id);
  }
  return id;
}

/** Wipe the per-user identity. Used by Settings → Clear my data. */
export function resetUserId(): void {
  if (!isBrowser()) return;
  localStorage.removeItem(USER_ID_KEY);
}
