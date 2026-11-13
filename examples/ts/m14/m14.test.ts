import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, test } from "vitest";
import { fixture, haveFfmpeg, loudnessLufs, makeClip, planEdl, run, score } from "./highlightReel.ts";

test("planEdl: greedy by score under budget, time order, frame-snapped margin", () => {
  const shots = [
    { start: 0, end: 2 },
    { start: 2, end: 3.52 },
    { start: 3.52, end: 6.04 },
    { start: 6.04, end: 8.04 },
  ];
  const plan = planEdl(shots, [0.4, 0, 1, 0.9], 3.3);
  expect(plan.entries.map((e) => e.shot)).toEqual([2, 3]);
  expect(plan.entries[0].srcIn).toBeCloseTo(3.72);
  expect(planEdl(shots, [0.1, 0.1, 0.1, 0.1], 10).entries).toEqual([]);
});

test("mock scorer", () => {
  expect(score("what a goal the crowd erupts", "striker celebrating")).toBe(1);
  expect(score("slow build up", "midfielders passing")).toBe(0);
});

describe.skipIf(!haveFfmpeg())("with real ffmpeg", () => {
  test("highlight reel end to end matches the Python plan", () => {
    const dir = mkdtempSync(join(tmpdir(), "m14-"));
    const src = makeClip(join(dir, "match.mp4"), fixture.shots);
    const res = run(src, join(dir, "reel.mp4"));
    expect(res.failures, res.trace.join("\n")).toEqual([]);
    expect(res.plan.entries.map((e) => [e.shot, e.srcIn, e.srcOut])).toEqual([
      [2, 3.72, 5.32],
      [4, 8.24, 9.84],
    ]);
    expect(loudnessLufs(join(dir, "reel.mp4"))).toBeCloseTo(-16, 0);
  }, 60_000);
});
