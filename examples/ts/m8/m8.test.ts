import { TestWorkflowEnvironment } from "@temporalio/testing";
import { Worker } from "@temporalio/worker";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, expect, test } from "vitest";
import * as activities from "./activities.ts";
import { ledger } from "./activities.ts";
import { PLAN, agentRun, approve, publishWithApproval, status } from "./workflows.ts";

// Time-skipping test server: downloaded by @temporalio/testing on first use.
let env: TestWorkflowEnvironment;
let worker: Worker;
let running: Promise<void>;
beforeAll(async () => {
  env = await TestWorkflowEnvironment.createTimeSkipping();
  worker = await Worker.create({
    connection: env.nativeConnection,
    taskQueue: "m8",
    workflowsPath: fileURLToPath(new URL("./workflows.ts", import.meta.url)),
    activities,
  });
  running = worker.run();
}, 120_000);
afterAll(async () => {
  worker?.shutdown();
  await running;
  await env?.teardown();
});

test("a lost activity after its side effect is retried without repeating the effect", async () => {
  ledger.failOnce.add("r1:6");
  const out = await env.client.workflow.execute(agentRun, { args: ["r1"], workflowId: "r1", taskQueue: "m8" });
  expect(out).toHaveLength(PLAN.length);
  expect(ledger.effects.size).toBe(10);
  expect(ledger.attempts.filter((k) => k === "r1:6")).toHaveLength(2);
}, 60_000);

test("approval can arrive days later; no approval expires after 7 days", async () => {
  const h = await env.client.workflow.start(publishWithApproval, { args: ["promo.mp4"], workflowId: "a1", taskQueue: "m8" });
  await env.sleep("3 days"); // skipped, not waited
  expect(await h.query(status)).toBe("waiting");
  await h.signal(approve, "arun");
  expect(await h.result()).toBe("published promo.mp4 (approved by arun)");
  const late = await env.client.workflow.execute(publishWithApproval, { args: ["old.mp4"], workflowId: "a2", taskQueue: "m8" });
  expect(late).toBe("expired: old.mp4 not approved");
}, 60_000);
