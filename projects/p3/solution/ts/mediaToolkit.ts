// P3 milestone 2 (TypeScript): the media-toolkit server on @modelcontextprotocol/server 2.4.0.
// A subset of the Python server: probe and loudness (same contract as M9 and the Rust server),
// detect_scenes, detect_silence, and transcode (preset allowlist, asks first with
// input_required). The Python server is the full toolkit; this one shows the same promises
// hold in another SDK.
import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { promisify } from "node:util";
import { McpServer, acceptedContent, inputRequired } from "@modelcontextprotocol/server";
import * as z from "zod/v4";
import { LoudnessResult, ProbeResult, parseFfprobe, parseLoudnorm } from "../../../../examples/ts/m9/mediaProbe.ts";

const run = promisify(execFile);
const BIG = { maxBuffer: 32 * 1024 * 1024, timeout: 120_000 };

export const PRESETS: Record<string, string[]> = {
  h264_360p: ["-vf", "scale=-2:360", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac"],
  h264_720p: ["-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac"],
  aac_audio: ["-vn", "-c:a", "aac", "-b:a", "128k"],
};

/** Relative paths only: no protocols (`concat:`, `http:`), no absolute paths, no `..`. */
export function safePath(root: string, rel: string): string | undefined {
  if (/^[A-Za-z][A-Za-z0-9+.-]*:/.test(rel)) return undefined;
  if (rel.startsWith("/") || rel.split(/[\\/]/).includes("..")) return undefined;
  return `${root}/${rel}`;
}

export function parseSceneCuts(stderr: string): number[] {
  return [...stderr.matchAll(/pts_time:([\d.]+)/g)].map((m) => Math.round(Number(m[1]) * 1000) / 1000);
}

export function parseSilences(stderr: string): { start: number; end: number }[] {
  const starts = [...stderr.matchAll(/silence_start: ([\d.]+)/g)].map((m) => Number(m[1]));
  const ends = [...stderr.matchAll(/silence_end: ([\d.]+)/g)].map((m) => Number(m[1]));
  return starts.slice(0, ends.length).map((s, i) => ({ start: s, end: ends[i] }));
}

const err = (text: string) => ({ content: [{ type: "text" as const, text }], isError: true });
const ok = <T extends Record<string, unknown>>(v: T) => ({
  content: [{ type: "text" as const, text: JSON.stringify(v) }],
  structuredContent: v,
});
const Confirm = z.object({ confirm: z.boolean() });
const READ = { readOnlyHint: true, openWorldHint: false };

export function buildMediaToolkit(root: string) {
  const server = new McpServer({ name: "media-toolkit-ts", version: "0.6.0" });
  const pathIn = z.object({ path: z.string().describe("Path relative to the media root") });

  server.registerTool(
    "probe",
    { description: "Probe a media file with ffprobe: duration and streams. Read-only.", inputSchema: pathIn, outputSchema: ProbeResult, annotations: READ },
    async ({ path }) => {
      const file = safePath(root, path);
      if (!file) return err(`path escapes media root: ${path}`);
      const out = await run("ffprobe", ["-v", "error", "-show_format", "-show_streams", "-of", "json", file], BIG);
      return ok(parseFfprobe(path, out.stdout));
    },
  );

  server.registerTool(
    "loudness",
    { description: "Measure integrated loudness (LUFS) and true peak with ffmpeg loudnorm. Read-only.", inputSchema: pathIn, outputSchema: LoudnessResult, annotations: READ },
    async ({ path }) => {
      const file = safePath(root, path);
      if (!file) return err(`path escapes media root: ${path}`);
      const out = await run("ffmpeg", ["-hide_banner", "-nostats", "-i", file, "-af", "loudnorm=print_format=json", "-f", "null", "-"], BIG);
      return ok(parseLoudnorm(path, out.stderr));
    },
  );

  server.registerTool(
    "detect_scenes",
    {
      description: "Scene-cut timestamps (seconds) where ffmpeg's scene score exceeds threshold (0-1). Read-only.",
      inputSchema: z.object({ path: z.string(), threshold: z.number().gt(0).lt(1).default(0.3) }),
      outputSchema: z.object({ path: z.string(), cuts: z.array(z.number()) }),
      annotations: READ,
    },
    async ({ path, threshold }) => {
      const file = safePath(root, path);
      if (!file) return err(`path escapes media root: ${path}`);
      const out = await run("ffmpeg", ["-hide_banner", "-nostats", "-i", file, "-an", "-vf", `select='gt(scene,${threshold})',showinfo`, "-f", "null", "-"], BIG);
      return ok({ path, cuts: parseSceneCuts(out.stderr) });
    },
  );

  server.registerTool(
    "detect_silence",
    {
      description: "Silent stretches (start/end seconds) below noise_db lasting at least min_s. Read-only.",
      inputSchema: z.object({ path: z.string(), noise_db: z.number().default(-40), min_s: z.number().positive().default(0.3) }),
      outputSchema: z.object({ path: z.string(), silences: z.array(z.object({ start: z.number(), end: z.number() })) }),
      annotations: READ,
    },
    async ({ path, noise_db, min_s }) => {
      const file = safePath(root, path);
      if (!file) return err(`path escapes media root: ${path}`);
      const out = await run("ffmpeg", ["-hide_banner", "-nostats", "-i", file, "-vn", "-af", `silencedetect=noise=${noise_db}dB:d=${min_s}`, "-f", "null", "-"], BIG);
      return ok({ path, silences: parseSilences(out.stderr) });
    },
  );

  server.registerTool(
    "transcode",
    {
      description: "Re-encode a file with a named preset (h264_360p, h264_720p, aac_audio). Asks first. Free-form ffmpeg arguments are not accepted.",
      inputSchema: z.object({ path: z.string(), preset: z.string(), out: z.string() }),
      outputSchema: z.object({ outputs: z.array(z.string()), duration_s: z.number() }),
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: false },
    },
    async ({ path, preset, out }, ctx) => {
      const src = safePath(root, path);
      const dst = safePath(root, out);
      if (!src || !dst) return err("path escapes media root");
      if (!(preset in PRESETS)) return err(`unknown preset ${JSON.stringify(preset)}; allowed: ${Object.keys(PRESETS).join(", ")}`);
      if (existsSync(dst)) return err(`${out} exists; transcode never overwrites`);
      const answer = acceptedContent(ctx.mcpReq.inputResponses, "confirm", Confirm);
      if (answer === undefined) {
        return inputRequired({
          inputRequests: { confirm: inputRequired.elicit({ message: `Transcode ${path} with preset ${preset}?`, requestedSchema: Confirm }) },
        });
      }
      if (!answer.confirm) return ok({ outputs: [], duration_s: 0 });
      await run("ffmpeg", ["-y", "-hide_banner", "-loglevel", "error", "-i", src, ...PRESETS[preset], dst], BIG);
      const probed = parseFfprobe(out, (await run("ffprobe", ["-v", "error", "-show_format", "-show_streams", "-of", "json", dst], BIG)).stdout);
      return ok({ outputs: [out], duration_s: probed.duration_s });
    },
  );

  return server;
}
