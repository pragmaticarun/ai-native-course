import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";
import { InMemoryTransport } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import { expect, test } from "vitest";
import { buildMediaProbe, fixtureRunner, parseLoudnorm, resolveInRoot } from "./mediaProbe.ts";

const FIXTURE = readFileSync(new URL("../../python/m9/fixtures/ffprobe_talk.json", import.meta.url), "utf8");

type Mode = "legacy" | "auto";

async function connect(onDelete: (f: string) => void, answer?: boolean, mode: Mode = "auto") {
  const [clientT, serverT] = InMemoryTransport.createLinkedPair();
  // serveStdio owns the era decision (2026-07-28 or 2025-11-25) and works over any
  // transport. A bare server.connect(transport) would only ever serve the 2025 era.
  const handle = serveStdio(() => buildMediaProbe("/media", fixtureRunner(FIXTURE), onDelete), {
    transport: serverT,
  });
  const asked: string[] = [];
  const client = new Client(
    { name: "m9-test", version: "1.0.0" },
    {
      capabilities: answer === undefined ? {} : { elicitation: { form: {} } },
      // The TS client defaults to "legacy" (2025-11-25 initialize); the Python client to "auto".
      versionNegotiation: { mode },
    },
  );
  if (answer !== undefined) {
    client.setRequestHandler("elicitation/create", async (req) => {
      asked.push(String((req.params as { message?: string }).message));
      return { action: "accept", content: { confirm: answer } };
    });
  }
  await client.connect(clientT);
  return {
    client,
    asked,
    close: async () => {
      await client.close();
      await handle.close();
    },
  };
}

const text = (r: unknown) => ((r as { content: { text: string }[] }).content[0] ?? { text: "" }).text;

test.each([
  ["auto", "2026-07-28"],
  ["legacy", "2025-11-25"],
] as const)("lists tools with annotations and output schemas (%s)", async (mode, version) => {
  const { client, close } = await connect(() => {}, undefined, mode);
  const { tools } = await client.listTools();
  expect(tools.map((t) => t.name)).toEqual(["probe", "loudness", "delete_clip"]);
  expect(tools[0]?.annotations?.readOnlyHint).toBe(true);
  expect(tools[0]?.outputSchema).toBeDefined();
  expect(tools[2]?.annotations?.destructiveHint).toBe(true);
  expect(client.getNegotiatedProtocolVersion()).toBe(version);
  await close();
});

test("probe returns structured content; escapes are refused", async () => {
  const { client, close } = await connect(() => {});
  const ok = await client.callTool({ name: "probe", arguments: { path: "talk.mp4" } });
  expect(ok.structuredContent).toMatchObject({ duration_s: 7200, streams: [{ codec_type: "video" }, {}] });
  const bad = await client.callTool({ name: "probe", arguments: { path: "../etc/passwd" } });
  expect(bad.isError).toBe(true);
  expect(text(bad)).toContain("escapes");
  await close();
});

test.each([
  [true, "deleted clip.mp4", 1, "auto"],
  [false, "kept clip.mp4", 0, "auto"],
  [true, "deleted clip.mp4", 1, "legacy"],
  [false, "kept clip.mp4", 0, "legacy"],
] as const)("delete_clip asks first (answer %s -> %s, deletions %i, mode %s)", async (answer, expected, deletions, mode) => {
  const deleted: string[] = [];
  const { client, asked, close } = await connect((f) => deleted.push(f), answer, mode);
  const r = await client.callTool({ name: "delete_clip", arguments: { path: "clip.mp4" } });
  expect(text(r)).toBe(expected);
  expect(asked).toEqual(["Permanently delete clip.mp4?"]);
  expect(deleted).toHaveLength(deletions);
  await close();
});

test("pure helpers", () => {
  expect(resolveInRoot("/m", "a/b.wav")).toBe("/m/a/b.wav");
  expect(resolveInRoot("/m", "a/../../x")).toBeUndefined();
  expect(parseLoudnorm("a", 'x {"y":1}\n{"input_i" : "-23.0", "input_tp" : "-2.5"}').integrated_lufs).toBe(-23);
});

// Cross-language: the TypeScript client against the Rust rmcp server over stdio, real ffmpeg.
const RUST_BIN =
  process.env.MEDIA_PROBE_RUST_BIN ??
  new URL("../../../rust/media-probe/target/debug/media-probe", import.meta.url).pathname;
const hasFfmpeg = (() => {
  try {
    execFileSync("ffmpeg", ["-version"], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
})();

// CI's rust job sets MEDIA_PROBE_REQUIRE_ALL=1: then a missing binary or ffmpeg fails instead of skipping.
const requireAll = process.env.MEDIA_PROBE_REQUIRE_ALL === "1";
test.skipIf(!requireAll && (!existsSync(RUST_BIN) || !hasFfmpeg))("TS client -> Rust server over stdio", async () => {
  const root = mkdtempSync(join(tmpdir(), "m9-"));
  execFileSync("ffmpeg", ["-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", join(root, "tone.wav")]);
  const client = new Client({ name: "m9-ts", version: "1.0.0" }, { versionNegotiation: { mode: "auto" } });
  await client.connect(new StdioClientTransport({ command: RUST_BIN, args: [root], stderr: "ignore" }));
  const names = (await client.listTools()).tools.map((t) => t.name).sort();
  expect(names).toEqual(["loudness", "probe"]);
  const probe = await client.callTool({ name: "probe", arguments: { path: "tone.wav" } });
  expect((probe.structuredContent as { duration_s: number }).duration_s).toBeCloseTo(2, 1);
  const escape = await client.callTool({ name: "probe", arguments: { path: "../x.wav" } });
  expect(escape.isError).toBe(true);
  expect(client.getNegotiatedProtocolVersion()).toBe("2026-07-28");
  await client.close();
});
