import { expect, test } from "vitest";
import { extractEvent } from "./structured.ts";
import { ask, convert } from "./unitConverter.ts";

test("tool loop converts a marathon", async () => {
  expect(await ask("marathon?")).toEqual({ text: "That is 26.2187 miles.", steps: 2 });
});

test("convert rejects unknown units", () => {
  expect(() => convert(1, "C", "F")).toThrow("unsupported");
});

test("structured output parses and validates", async () => {
  expect(await extractEvent("...")).toEqual({ title: "Rust meetup", date: "2026-11-20", location: "Bengaluru" });
});

test("structured output rejects a missing field", async () => {
  await expect(extractEvent("...", '{"title":"x","date":"y"}')).rejects.toThrow();
});
