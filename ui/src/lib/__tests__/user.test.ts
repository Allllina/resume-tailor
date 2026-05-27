// Layer 1 — sample unit test proving the Vitest + jsdom infra works.
// Tests `getUserId` / `resetUserId` from `@/lib/user` — pure logic that
// reads/writes localStorage. No React components, no API calls.
//
// Add more lib unit tests next to this file. See docs/TESTING.md.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getUserId, resetUserId } from "@/lib/user";

describe("getUserId", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    localStorage.clear();
    vi.unstubAllEnvs();
  });

  it("defaults to the single-user MVP workspace", () => {
    const id = getUserId();
    expect(id).toBe("jingwen-default");
    expect(localStorage.getItem("rt:user_id")).toBeNull();
  });

  it("returns a UUID-shaped id on first call", () => {
    vi.stubEnv("VITE_ENABLE_MULTI_USER", "true");
    const id = getUserId();
    expect(id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
  });

  it("persists the id across calls (same browser session)", () => {
    vi.stubEnv("VITE_ENABLE_MULTI_USER", "true");
    const first = getUserId();
    const second = getUserId();
    expect(second).toBe(first);
  });

  it("writes the id to localStorage under the rt: namespace", () => {
    vi.stubEnv("VITE_ENABLE_MULTI_USER", "true");
    const id = getUserId();
    expect(localStorage.getItem("rt:user_id")).toBe(id);
  });

  it("resetUserId wipes the persisted id", () => {
    vi.stubEnv("VITE_ENABLE_MULTI_USER", "true");
    const first = getUserId();
    resetUserId();
    expect(localStorage.getItem("rt:user_id")).toBeNull();
    const second = getUserId();
    expect(second).not.toBe(first);
  });
});
