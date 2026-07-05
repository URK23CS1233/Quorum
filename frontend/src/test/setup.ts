import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Ensure the jsdom DOM and any mounted React trees are reset between tests.
afterEach(() => {
  cleanup();
});
