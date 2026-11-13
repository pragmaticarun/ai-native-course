// M7 worked example (TypeScript): the document-triage graph in LangGraph.js.
// router -> parallel extractors (Send) -> supervisor merge -> interrupt for approval.
// Tested with @langchain/langgraph 1.7.3 (see CHANGELOG: 1.7.4 was too new for pnpm's
// minimum-release-age policy on the day this was written).
import { Annotation, Command, END, MemorySaver, Send, START, StateGraph, interrupt } from "@langchain/langgraph";

const FIELDS: Record<string, string[]> = { invoice: ["amount", "due_date"], bug_report: ["device", "version"] };
const PATTERNS: Record<string, RegExp> = {
  amount: /(?:INR|USD|EUR)\s?[\d,]+(?:\.\d\d)?/,
  due_date: /\b20\d\d-\d\d-\d\d\b/,
  device: /\b(?:Galaxy|Pixel)\s[\w ]+?(?=,|\.|$)/,
  version: /\bv?\d+\.\d+(?:\.\d+)?\b/,
};

export const Doc = Annotation.Root({
  text: Annotation<string>,
  kind: Annotation<string>,
  // reducer: parallel extractors append instead of overwriting each other
  fields: Annotation<{ field: string; value: string | null }[]>({ reducer: (a, b) => a.concat(b), default: () => [] }),
  issues: Annotation<string[]>,
  decision: Annotation<string>,
  filed: Annotation<string>,
});
type DocState = typeof Doc.State;

const route = (s: DocState) => ({ kind: /invoice/i.test(s.text) ? "invoice" : "bug_report" });
const fanOut = (s: DocState) => FIELDS[s.kind].map((field) => new Send("extract", { text: s.text, field }));
const extract = (job: { text: string; field: string }) => ({
  fields: [{ field: job.field, value: job.text.match(PATTERNS[job.field])?.[0] ?? null }],
});
const supervise = (s: DocState) => ({ issues: s.fields.filter((f) => f.value === null).map((f) => `missing ${f.field}`) });
const approve = (s: DocState) => {
  if (s.issues.length === 0) return new Command({ goto: "file", update: { decision: "auto" } });
  const answer = interrupt({ kind: s.kind, issues: s.issues }) as string;
  return new Command({ goto: answer === "approve" ? "file" : END, update: { decision: answer } });
};
const file = (s: DocState) => ({ filed: `${s.kind}:${s.fields.map((f) => `${f.field}=${f.value}`).sort().join(",")}` });

export function buildTriage() {
  return new StateGraph(Doc)
    .addNode("route", route)
    .addNode("extract", extract)
    .addNode("supervise", supervise)
    .addNode("approve", approve, { ends: ["file", END] })
    .addNode("file", file)
    .addEdge(START, "route")
    .addConditionalEdges("route", fanOut, ["extract"])
    .addEdge("extract", "supervise")
    .addEdge("supervise", "approve")
    .addEdge("file", END)
    .compile({ checkpointer: new MemorySaver() });
}
