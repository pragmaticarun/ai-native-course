export type Outcome<T> = { ok: true; value: T } | { ok: false; error: string; attempts: number };
export interface FanOutOptions {
  limit: number;
  retries: number;
  maxFailures: number;
}

export async function fanOut<I, O>(
  items: I[],
  fn: (item: I, index: number) => Promise<O>,
  opts: FanOutOptions,
): Promise<{ results: Outcome<O>[]; peak: number }> {
  if (opts.limit < 1) throw new RangeError("limit must be >= 1");
  const results: Outcome<O>[] = new Array(items.length);
  let next = 0;
  let failures = 0;
  let active = 0;
  let peak = 0;

  async function attempt(i: number): Promise<Outcome<O>> {
    let error = "";
    for (let a = 1; a <= 1 + opts.retries; a++) {
      active++;
      peak = Math.max(peak, active);
      try {
        return { ok: true, value: await fn(items[i] as I, i) };
      } catch (e) {
        error = e instanceof Error ? e.message : String(e);
      } finally {
        active--;
      }
    }
    return { ok: false, error, attempts: 1 + opts.retries };
  }

  async function lane() {
    while (next < items.length && failures < opts.maxFailures) {
      const i = next++;
      const r = await attempt(i);
      if (!r.ok) failures++;
      results[i] = r;
    }
  }
  await Promise.all(Array.from({ length: Math.min(opts.limit, items.length) }, lane));
  for (let i = 0; i < items.length; i++) results[i] ??= { ok: false, error: "skipped", attempts: 0 };
  return { results, peak };
}
