// L7.4 (TypeScript): bounded fan-out without a framework. A semaphore keeps at most
// `limit` workers running, results keep input order, and failures are collected
// instead of rejecting the whole batch (Promise.allSettled semantics with a limit).
export type Settled<T> = { ok: true; value: T } | { ok: false; error: string };

export async function mapLimit<I, O>(items: I[], limit: number, fn: (item: I, index: number) => Promise<O>): Promise<Settled<O>[]> {
  if (limit < 1) throw new RangeError("limit must be >= 1");
  const out: Settled<O>[] = new Array(items.length);
  let next = 0;
  async function lane() {
    while (next < items.length) {
      const i = next++;
      try {
        out[i] = { ok: true, value: await fn(items[i], i) };
      } catch (e) {
        out[i] = { ok: false, error: e instanceof Error ? e.message : String(e) };
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, lane));
  return out;
}
