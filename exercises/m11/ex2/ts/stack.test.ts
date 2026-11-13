import { expect, test } from "vitest";

const variant = process.env.EXERCISE_VARIANT ?? "solution";
const { splitStack } = (await import(`./${variant}/stack.ts`)) as typeof import("./solution/stack.ts");

// The agent's 960-line "add clip tagging" PR, as logical units.
const UNITS = [
  { name: "model", lines: 180, dependsOn: [] },
  { name: "store", lines: 220, dependsOn: ["model"] },
  { name: "routes", lines: 150, dependsOn: ["store"] },
  { name: "tests", lines: 200, dependsOn: ["routes"] },
  { name: "docs", lines: 120, dependsOn: ["routes"] },
  { name: "table", lines: 90, dependsOn: ["store"] },
];

test("a reviewable stack under 400 lines per PR", () => {
  expect(splitStack(UNITS, 400)).toEqual([["model", "store"], ["routes", "tests"], ["docs", "table"]]);
});

test("dependency order even when the input isn't", () => {
  const shuffled = [UNITS[3], UNITS[4], UNITS[1], UNITS[0], UNITS[5], UNITS[2]];
  expect(splitStack(shuffled, 2000)).toEqual([["model", "store", "table", "routes", "tests", "docs"]]);
  expect(splitStack([{ name: "huge", lines: 900, dependsOn: [] }, { name: "small", lines: 10, dependsOn: [] }], 400)).toEqual([["huge"], ["small"]]);
});

test("cycles and unknown dependencies are errors", () => {
  expect(() => splitStack([{ name: "a", lines: 1, dependsOn: ["b"] }, { name: "b", lines: 1, dependsOn: ["a"] }], 400)).toThrow(/cycle/);
  expect(() => splitStack([{ name: "a", lines: 1, dependsOn: ["ghost"] }], 400)).toThrow(/unknown/);
});
