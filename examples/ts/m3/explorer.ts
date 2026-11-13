// L3.3: the read-only explorer agent with the AI SDK. The step budget is `stopWhen`.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve, sep } from "node:path";
import { generateText, isStepCount, tool } from "ai";
import { z } from "zod";
import { getModel, scriptedModel, text, toolCall } from "../lib/mock.ts";

export function makeTools(rootDir: string) {
  const root = resolve(rootDir);
  const safe = (rel: string) => {
    const p = resolve(root, rel);
    if (p !== root && !p.startsWith(root + sep)) throw new Error(`${rel} is outside the sandbox`);
    return p;
  };
  const walk = (dir: string): string[] =>
    readdirSync(dir).filter((n) => !n.startsWith(".")).flatMap((n) => {
      const p = join(dir, n);
      return statSync(p).isDirectory() ? walk(p) : [p];
    });
  return {
    grep: tool({
      description: "Find lines containing a literal string (read-only).",
      inputSchema: z.object({ pattern: z.string(), path: z.string().default(".") }),
      execute: async ({ pattern, path }) =>
        walk(safe(path)).flatMap((f) =>
          readFileSync(f, "utf8").split("\n").flatMap((line, i) =>
            line.includes(pattern) ? [`${relative(root, f)}:${i + 1}: ${line.trim()}`] : []),
        ).join("\n") || "no matches",
    }),
    read_file: tool({
      description: "Read a text file (read-only, truncated).",
      inputSchema: z.object({ path: z.string() }),
      execute: async ({ path }) => readFileSync(safe(path), "utf8").slice(0, 2000),
    }),
  };
}

type ToolMsg = { role: string; content: Array<{ output?: { value?: unknown } }> };

export const mockExplorer = () =>
  scriptedModel((prompt) => {
    const outputs = (prompt as ToolMsg[]).filter((m) => m.role === "tool")
      .map((m) => String(m.content[0]?.output?.value ?? ""));
    if (outputs.length === 0) return [toolCall("grep", { pattern: "def main", path: "." })];
    if (outputs[0] === "no matches") return [text("I found no `def main` in this tree.")];
    return [text(`The entry point is main() in ${outputs[0].split(":")[0]}.`)];
  });

export async function explore(root: string, question: string, maxSteps = 6) {
  const result = await generateText({
    model: await getModel(mockExplorer()),
    system: "You explore a codebase with read-only tools.",
    prompt: question,
    tools: makeTools(root),
    stopWhen: isStepCount(maxSteps),
  });
  return result.text;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log(await explore(process.argv[2] ?? ".", "Where is the entry point?"));
}
