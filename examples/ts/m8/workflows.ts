// M8 (TypeScript): Temporal workflows. Workflow code is deterministic and replayed;
// all I/O happens in activities. Bundled by the Temporal worker (webpack), so it may
// only import @temporalio/workflow and types.
import { condition, defineQuery, defineSignal, proxyActivities, setHandler } from "@temporalio/workflow";
import type * as activities from "./activities.ts";

const { runStep } = proxyActivities<typeof activities>({
  startToCloseTimeout: "30s",
  retry: { initialInterval: "100ms" },
});

export const PLAN = ["fetch_ticket", "probe", "transcode", "transcribe", "upload", "summarise", "notify", "label", "comment", "close"];

export async function agentRun(runId: string): Promise<string[]> {
  const out: string[] = [];
  for (const [i, tool] of PLAN.entries()) out.push(await runStep(runId, i + 1, tool));
  return out;
}

export const approve = defineSignal<[string]>("approve");
export const status = defineQuery<string>("status");

/** Waits up to 7 days for a human. Durable timers: no process sleeps for a week. */
export async function publishWithApproval(asset: string): Promise<string> {
  let approver: string | undefined;
  let state = "waiting";
  setHandler(approve, (by) => {
    approver = by;
  });
  setHandler(status, () => state);
  const approved = await condition(() => approver !== undefined, "7 days");
  state = approved ? `published ${asset} (approved by ${approver})` : `expired: ${asset} not approved`;
  return state;
}
