export type Question = { q: string; relevant: string[] };
export type Retriever = (q: string) => string[];

export function recallAtK(ranked: string[], relevant: string[], k: number): number {
  // TODO
  return 0;
}

export function compare(questions: Question[], retrievers: Record<string, Retriever>, k: number) {
  // TODO
  return {} as Record<string, { meanRecall: number; wins: number }>;
}
