// M9 worked example (TypeScript): the "media-probe" MCP server on @modelcontextprotocol/server 2.4.0.
// Same contract as the Python, Rust and Kotlin servers. The destructive tool asks first:
// on the 2026-07-28 revision it returns an `input_required` result (MRTR) and the client
// retries with the user's answer in `ctx.mcpReq.inputResponses`.
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { McpServer, acceptedContent, inputRequired } from "@modelcontextprotocol/server";
import * as z from "zod/v4";

export interface Runner {
  ffprobe(file: string): Promise<string>;
  loudnorm(file: string): Promise<string>;
}

const run = promisify(execFile);

export const ffmpegRunner: Runner = {
  async ffprobe(file) {
    const args = ["-v", "error", "-show_format", "-show_streams", "-of", "json", file];
    return (await run("ffprobe", args)).stdout;
  },
  async loudnorm(file) {
    const args = ["-hide_banner", "-nostats", "-i", file, "-af", "loudnorm=print_format=json", "-f", "null", "-"];
    return (await run("ffmpeg", args, { maxBuffer: 16 * 1024 * 1024 })).stderr;
  },
};

export function fixtureRunner(ffprobeJson: string, lufs = -16.2, peak = -1.4): Runner & { calls: string[] } {
  const calls: string[] = [];
  return {
    calls,
    async ffprobe(file) {
      calls.push(`ffprobe ${file}`);
      return ffprobeJson;
    },
    async loudnorm(file) {
      calls.push(`loudnorm ${file}`);
      return `[Parsed_loudnorm_0]\n{"input_i" : "${lufs}", "input_tp" : "${peak}"}\n`;
    },
  };
}

const Stream = z.object({
  codec_type: z.string(),
  codec_name: z.string(),
  width: z.number().int().optional(),
  height: z.number().int().optional(),
  sample_rate: z.number().int().optional(),
});
export const ProbeResult = z.object({ path: z.string(), duration_s: z.number(), streams: z.array(Stream) });
export const LoudnessResult = z.object({ path: z.string(), integrated_lufs: z.number(), true_peak_dbtp: z.number() });

export function parseFfprobe(path: string, text: string): z.infer<typeof ProbeResult> {
  const data = JSON.parse(text) as { streams?: Record<string, unknown>[]; format: { duration: string } };
  const streams = (data.streams ?? []).map((s) => {
    const out: z.infer<typeof Stream> = {
      codec_type: String(s.codec_type ?? "unknown"),
      codec_name: String(s.codec_name ?? "unknown"),
    };
    for (const k of ["width", "height", "sample_rate"] as const) if (k in s) out[k] = Number(s[k]);
    return out;
  });
  return { path, duration_s: Number(data.format.duration), streams };
}

export function parseLoudnorm(path: string, stderr: string): z.infer<typeof LoudnessResult> {
  const block = JSON.parse(stderr.slice(stderr.lastIndexOf("{"), stderr.lastIndexOf("}") + 1)) as Record<
    string,
    string
  >;
  return { path, integrated_lufs: Number(block.input_i), true_peak_dbtp: Number(block.input_tp) };
}

/** Relative paths only, no `..`: the server never reads outside its media root. */
export function resolveInRoot(root: string, rel: string): string | undefined {
  if (rel.startsWith("/") || rel.split(/[\\/]/).includes("..")) return undefined;
  return `${root}/${rel}`;
}

const err = (text: string) => ({ content: [{ type: "text" as const, text }], isError: true });
const Confirm = z.object({ confirm: z.boolean() });

export function buildMediaProbe(root: string, runner: Runner, onDelete: (file: string) => void) {
  const server = new McpServer({ name: "media-probe", version: "0.3.0" });
  const pathIn = z.object({ path: z.string().describe("Path relative to the media root") });

  server.registerTool(
    "probe",
    {
      description: "Probe a media file with ffprobe: duration and streams. Read-only.",
      inputSchema: pathIn,
      outputSchema: ProbeResult,
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async ({ path }) => {
      const file = resolveInRoot(root, path);
      if (!file) return err(`path escapes media root: ${path}`);
      const result = parseFfprobe(path, await runner.ffprobe(file));
      return { content: [{ type: "text", text: JSON.stringify(result) }], structuredContent: result };
    },
  );

  server.registerTool(
    "loudness",
    {
      description: "Measure integrated loudness (LUFS) and true peak with ffmpeg loudnorm. Read-only.",
      inputSchema: pathIn,
      outputSchema: LoudnessResult,
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async ({ path }) => {
      const file = resolveInRoot(root, path);
      if (!file) return err(`path escapes media root: ${path}`);
      const result = parseLoudnorm(path, await runner.loudnorm(file));
      return { content: [{ type: "text", text: JSON.stringify(result) }], structuredContent: result };
    },
  );

  server.registerTool(
    "delete_clip",
    {
      description: "Delete a clip from the media root. Asks the user to confirm every time.",
      inputSchema: pathIn,
      annotations: { destructiveHint: true, idempotentHint: true },
    },
    async ({ path }, ctx) => {
      const file = resolveInRoot(root, path);
      if (!file) return err(`path escapes media root: ${path}`);
      const answer = acceptedContent(ctx.mcpReq.inputResponses, "confirm", Confirm);
      if (answer === undefined) {
        // First round trip: no answer yet, so ask. The client retries with it.
        return inputRequired({
          inputRequests: {
            confirm: inputRequired.elicit({ message: `Permanently delete ${path}?`, requestedSchema: Confirm }),
          },
        });
      }
      if (!answer.confirm) return { content: [{ type: "text", text: `kept ${path}` }] };
      onDelete(file);
      return { content: [{ type: "text", text: `deleted ${path}` }] };
    },
  );

  return server;
}
