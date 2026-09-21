import "@testing-library/jest-dom";
import { beforeEach } from "vitest";
import { clearApiCache } from "@/lib/api";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

global.ResizeObserver = ResizeObserverStub as any;

beforeEach(() => {
  clearApiCache();
});