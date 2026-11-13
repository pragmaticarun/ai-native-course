import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test } from "vitest";
import { explore, makeTools } from "./explorer.ts";

function repo() {
  const dir = mkdtempSync(join(tmpdir(), "explorer-"));
  mkdirSync(join(dir, "src"));
  writeFileSync(join(dir, "src", "app.py"), "def main():\n    pass\n");
  return dir;
}

test("explorer answers from the grep observation", async () => {
  expect(await explore(repo(), "entry?")).toBe("The entry point is main() in src/app.py.");
});

test("sandbox blocks traversal", async () => {
  const tools = makeTools(repo());
  await expect(
    tools.read_file.execute!({ path: "../../etc/passwd" }, { toolCallId: "t", messages: [], context: {} }),
  ).rejects.toThrow("outside the sandbox");
});
