// P3 evals (TypeScript): the TS toolkit's guards and parsers. The cross-language contract
// (Python client vs Python, TS and Rust servers) runs from projects/p3/evals/test_p3.py.
import { expect, test } from "vitest";

const variant = process.env.PROJECT_VARIANT ?? "solution";
const m = (await import(`../${variant}/ts/mediaToolkit.ts`)) as typeof import("../solution/ts/mediaToolkit.ts");

test("paths: protocols, absolute paths and .. are refused", () => {
  expect(m.safePath("/m", "clips/a.mp4")).toBe("/m/clips/a.mp4");
  for (const bad of ["../x.mp4", "/etc/passwd", "concat:a.mp4|b.mp4", "http://evil.example/a.m3u8"]) {
    expect(m.safePath("/m", bad)).toBeUndefined();
  }
});

test("presets are a closed allowlist of fixed argument lists", () => {
  expect(Object.keys(m.PRESETS).sort()).toEqual(["aac_audio", "h264_360p", "h264_720p"]);
  for (const args of Object.values(m.PRESETS)) {
    expect(args).not.toContain("-f");
    expect(args.some((a) => a.includes("://"))).toBe(false);
  }
});

test("parsers read ffmpeg's stderr", () => {
  expect(m.parseSceneCuts("x pts_time:2.0 y\nz pts_time:3.52 w")).toEqual([2, 3.52]);
  expect(m.parseSilences("silence_start: 2.0\nsilence_end: 3.52 | silence_duration: 1.52\nsilence_start: 9")).toEqual([{ start: 2, end: 3.52 }]);
});
