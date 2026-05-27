// Vitest global setup — runs once before each test file.
// Imports @testing-library/jest-dom matchers (toBeInTheDocument, toBeDisabled, etc.)
// so component tests can assert against DOM state ergonomically.
//
// See docs/TESTING.md Layer 2 for component test patterns.
import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom 29 ships with a stub Storage that doesn't expose `clear`/`getItem`/etc
// as proper functions — tests that touch `localStorage.clear()` throw
// `TypeError: localStorage.clear is not a function`. Provide an in-memory
// polyfill so any code reading/writing storage in tests Just Works.
class InMemoryStorage implements Storage {
  private store: Map<string, string> = new Map();
  get length(): number {
    return this.store.size;
  }
  clear(): void {
    this.store.clear();
  }
  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }
  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }
  removeItem(key: string): void {
    this.store.delete(key);
  }
  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}
vi.stubGlobal("localStorage", new InMemoryStorage());
vi.stubGlobal("sessionStorage", new InMemoryStorage());

// Auto-cleanup after each test — prevents DOM leakage across test files.
afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
});
