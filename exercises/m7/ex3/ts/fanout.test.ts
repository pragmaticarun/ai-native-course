import { expect, test } from "vitest";

const variant = process.env.EXERCISE_VARIANT ?? "solution";
const { fanOut } = (await import(`./${variant}/fanout.ts`)) as typeof import("./solution/fanout.ts");

const tick = (ms = 2) => new Promise((r) => setTimeout(r, ms));

test("caps concurrency and keeps order", async () => {
  const { results, peak } = await fanOut(
    [1, 2, 3, 4, 5, 6, 7],
    async (n) => {
      await tick(3 + (n % 3));
      return n * 10;
    },
    { limit: 3, retries: 0, maxFailures: 99 },
  );
  expect(peak).toBe(3);
  expect(results.map((r) => (r.ok ? r.value : null))).toEqual([10, 20, 30, 40, 50, 60, 70]);
});

test("retries transient failures", async () => {
  const seen = new Map<number, number>();
  const { results } = await fanOut(
    ["a", "b", "c"],
    async (_s, i) => {
      seen.set(i, (seen.get(i) ?? 0) + 1);
      await tick();
      if (i === 1 && (seen.get(i) ?? 0) < 3) throw new Error("OCR model timed out");
      return i;
    },
    { limit: 2, retries: 2, maxFailures: 99 },
  );
  expect(results[1]).toEqual({ ok: true, value: 1 });
  expect(seen.get(1)).toBe(3);
});

test("stops starting work after the failure budget", async () => {
  const started: number[] = [];
  const { results } = await fanOut(
    Array.from({ length: 10 }, (_, i) => i),
    async (n) => {
      started.push(n);
      await tick();
      if (n < 3) throw new Error(`bad scene ${n}`);
      return n;
    },
    { limit: 1, retries: 1, maxFailures: 2 },
  );
  expect(results[0]).toEqual({ ok: false, error: "bad scene 0", attempts: 2 });
  expect(results[1]).toEqual({ ok: false, error: "bad scene 1", attempts: 2 });
  expect(results.slice(2).every((r) => !r.ok && r.error === "skipped" && r.attempts === 0)).toBe(true);
  expect(started).toEqual([0, 0, 1, 1]);
});

test("rejects a zero limit", async () => {
  await expect(fanOut([1], async (n) => n, { limit: 0, retries: 0, maxFailures: 1 })).rejects.toThrow(RangeError);
});
