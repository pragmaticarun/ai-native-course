import { expect, test } from "vitest";

const variant = process.env.EXERCISE_VARIANT ?? "solution";
const { recallAtK, compare } = (await import(`./${variant}/retrieval.ts`)) as typeof import("./solution/retrieval.ts");

const DOCS: Record<string, string> = {
  "config.py": "def parse_config(path): read the settings file",
  "net.py": "def open_socket(host): connect to the server",
  "audio.py": "def normalise_loudness(clip): ebur128 loudness target",
};

const grep = (q: string) => Object.keys(DOCS).filter((id) => DOCS[id].includes(q));
const trigrams = (s: string) => new Set(Array.from({ length: Math.max(0, s.length - 2) }, (_, i) => s.slice(i, i + 3).toLowerCase()));
const fuzzy = (q: string) => {
  const t = trigrams(q);
  const score = (id: string) => [...trigrams(DOCS[id])].filter((x) => t.has(x)).length;
  return Object.keys(DOCS).sort((a, b) => score(b) - score(a));
};

test("recall@k", () => {
  expect(recallAtK(["a", "b", "c"], ["c", "d"], 2)).toBe(0);
  expect(recallAtK(["a", "b", "c"], ["c", "d"], 3)).toBe(0.5);
  expect(recallAtK(["a"], [], 1)).toBe(0);
});

test("compare grep vs fuzzy", () => {
  const questions = [
    { q: "parse_config", relevant: ["config.py"] },
    { q: "loudness normalization", relevant: ["audio.py"] },
    { q: "open_socket", relevant: ["net.py"] },
  ];
  const r = compare(questions, { grep, fuzzy }, 1);
  expect(r.grep.meanRecall).toBeCloseTo(2 / 3);
  expect(r.fuzzy.meanRecall).toBeCloseTo(1);
  expect(r.grep.wins).toBe(0);
  expect(r.fuzzy.wins).toBe(1);
});
