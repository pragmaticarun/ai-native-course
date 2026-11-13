import { afterEach, expect, test, vi } from "vitest";
import { getModel, scriptedModel, text } from "../lib/mock.ts";
import { hello } from "./hello.ts";

afterEach(() => vi.unstubAllEnvs());

test("hello uses the mock model by default", async () => {
  expect(await hello("Ada")).toBe("Hello, Ada! (mock model, no network used)");
});

test("live mode needs a model id", async () => {
  vi.stubEnv("COURSE_LLM_PROVIDER", "openai");
  vi.stubEnv("COURSE_LLM_MODEL", "");
  await expect(getModel(scriptedModel(() => [text("x")]))).rejects.toThrow("COURSE_LLM_MODEL");
});

test("unknown providers are rejected", async () => {
  vi.stubEnv("COURSE_LLM_PROVIDER", "nope");
  vi.stubEnv("COURSE_LLM_MODEL", "m");
  await expect(getModel(scriptedModel(() => [text("x")]))).rejects.toThrow("Unknown");
});
