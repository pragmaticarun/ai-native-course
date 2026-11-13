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
  // TODO: limit concurrency, retry, stop after maxFailures. This runs everything at once.
  void opts;
  const results = await Promise.all(
    items.map(async (it, i): Promise<Outcome<O>> => {
      try {
        return { ok: true, value: await fn(it, i) };
      } catch (e) {
        return { ok: false, error: String(e), attempts: 1 };
      }
    }),
  );
  return { results, peak: items.length };
}
