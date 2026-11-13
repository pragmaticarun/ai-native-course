export type Question = { q: string; relevant: string[] };
export type Retriever = (q: string) => string[];

export function recallAtK(ranked: string[], relevant: string[], k: number): number {
  if (relevant.length === 0) return 0;
  const top = new Set(ranked.slice(0, k));
  return relevant.filter((r) => top.has(r)).length / relevant.length;
}

export function compare(questions: Question[], retrievers: Record<string, Retriever>, k: number) {
  const names = Object.keys(retrievers);
  const out: Record<string, { meanRecall: number; wins: number }> = {};
  for (const n of names) out[n] = { meanRecall: 0, wins: 0 };
  for (const { q, relevant } of questions) {
    const scores = names.map((n) => recallAtK(retrievers[n](q), relevant, k));
    names.forEach((n, i) => {
      out[n].meanRecall += scores[i] / questions.length;
      if (scores.every((s, j) => j === i || scores[i] > s)) out[n].wins += 1;
    });
  }
  return out;
}
