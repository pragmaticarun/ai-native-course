import { Client } from "@modelcontextprotocol/client";
import { InMemoryTransport, McpServer } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import { expect, test } from "vitest";
import * as z from "zod/v4";

const variant = process.env.EXERCISE_VARIANT ?? "solution";
const { checkScopes, visibleTools, guard } = (await import(`./${variant}/scopes.ts`)) as typeof import("./solution/scopes.ts");

const POLICY = {
  probe: ["media:read"],
  loudness: ["media:read"],
  delete_clip: ["media:read", "media:delete"],
  publish: ["media:publish", "media:read"],
};

test("checkScopes", () => {
  expect(checkScopes(POLICY, "probe", ["media:read"])).toEqual({ ok: true });
  expect(checkScopes(POLICY, "publish", [])).toEqual({ ok: false, missing: ["media:publish", "media:read"] });
  expect(checkScopes(POLICY, "format_disk", ["admin"])).toEqual({ ok: false, missing: ["<no policy>"] });
});

test("visibleTools hides what the token can't call", () => {
  expect(visibleTools(POLICY, ["media:read"])).toEqual(["loudness", "probe"]);
  expect(visibleTools(POLICY, ["media:read", "media:delete"])).toEqual(["delete_clip", "loudness", "probe"]);
});

test("guard enforces scopes inside a real MCP server", async () => {
  const deleted: string[] = [];
  const granted = ["media:read"]; // a read-only token
  const factory = () => {
    const server = new McpServer({ name: "scoped", version: "1.0.0" });
    server.registerTool(
      "delete_clip",
      { description: "Delete a clip", inputSchema: z.object({ path: z.string() }) },
      guard(POLICY, () => granted, "delete_clip", async ({ path }: { path: string }) => {
        deleted.push(path);
        return { content: [{ type: "text", text: `deleted ${path}` }] };
      }),
    );
    return server;
  };
  const [clientT, serverT] = InMemoryTransport.createLinkedPair();
  const handle = serveStdio(factory, { transport: serverT });
  const client = new Client({ name: "t", version: "1" }, { versionNegotiation: { mode: "auto" } });
  await client.connect(clientT);

  const denied = await client.callTool({ name: "delete_clip", arguments: { path: "a.mp4" } });
  expect(denied.isError).toBe(true);
  expect((denied.content as { text: string }[])[0]?.text).toBe("insufficient scope: media:delete");
  expect(deleted).toEqual([]);

  granted.push("media:delete");
  const ok = await client.callTool({ name: "delete_clip", arguments: { path: "a.mp4" } });
  expect(ok.isError).toBeFalsy();
  expect(deleted).toEqual(["a.mp4"]);
  await client.close();
  await handle.close();
});
