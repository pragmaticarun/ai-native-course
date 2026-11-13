// M8 (TypeScript): activities for the durable agent run. The ledger stands in for the
// outside world; `effects` is keyed by an idempotency key so a retry never repeats a
// side effect. In production the ledger is your database / the remote API's own
// idempotency-key support.
import { Context } from "@temporalio/activity";

export const ledger = { effects: new Map<string, string>(), attempts: [] as string[], failOnce: new Set<string>() };

export async function runStep(runId: string, index: number, tool: string): Promise<string> {
  const key = `${runId}:${index}`;
  ledger.attempts.push(key);
  if (!ledger.effects.has(key)) ledger.effects.set(key, `${tool} ok`);
  if (ledger.failOnce.delete(key)) throw new Error(`worker lost after side effect of step ${index}`);
  Context.current().heartbeat(index);
  return ledger.effects.get(key)!;
}
