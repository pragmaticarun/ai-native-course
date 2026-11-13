import { expect, test } from "vitest";
import { runWithApproval } from "./approval.ts";

test("denied: tool never runs and the model sees the reason", async () => {
  const r = await runWithApproval(() => ({ approved: false, reason: "keep for the minutes" }));
  expect(r).toEqual({ pausedFor: ["delete_recording"], deleted: [], text: "Not deleted: keep for the minutes" });
});

test("approved: tool runs exactly once after the human says yes", async () => {
  const seen: unknown[] = [];
  const r = await runWithApproval((call) => (seen.push(call.input), { approved: true, reason: "duplicate of the upload" }));
  expect(seen).toEqual([{ name: "meeting.m4a" }]);
  expect(r.deleted).toEqual(["meeting.m4a"]);
  expect(r.text).toBe("Done: deleted meeting.m4a");
});
