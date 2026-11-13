// M14 worked example, TypeScript version: the "highlight reel" agent.
// probe -> scene detect -> (fixed) transcript -> score -> EDL -> concat + two-pass loudnorm -> verify.
// ffmpeg/ffprobe are real (execFileSync with argv arrays, never a shell string); the transcript and
// frame captions are mock-model outputs from ../../python/m14/fixtures/highlight.json.
import { execFileSync, spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";

export const FPS = 25;
export type Shot = { color: string; seconds: number; tone_hz: number | null };
export type Segment = { start: number; end: number; text: string };
export type Cut = { start: number; end: number };
export type EdlEntry = { shot: number; srcIn: number; srcOut: number; score: number };
export type Plan = { entries: EdlEntry[]; targetLufs: number };

export const fixture = JSON.parse(
  readFileSync(new URL("../../python/m14/fixtures/highlight.json", import.meta.url), "utf8"),
) as { shots: Shot[]; transcript: Segment[]; captions: string[] };

export function haveFfmpeg(): boolean {
  return spawnSync("ffmpeg", ["-version"]).status === 0 && spawnSync("ffprobe", ["-version"]).status === 0;
}

function ff(args: string[]): string {
  const r = spawnSync("ffmpeg", args, { encoding: "utf8", timeout: 60_000 });
  if (r.status !== 0) throw new Error(`ffmpeg failed: ${r.stderr.trim().split("\n").at(-1)}`);
  return r.stderr;
}

export function makeClip(out: string, shots: Shot[]): string {
  const args = ["-y", "-loglevel", "error"];
  for (const s of shots) {
    args.push("-f", "lavfi", "-i", `color=c=${s.color}:s=320x240:r=${FPS}:d=${s.seconds}`);
    const a = s.tone_hz
      ? `sine=frequency=${s.tone_hz}:sample_rate=48000:duration=${s.seconds}`
      : `anullsrc=r=48000:cl=mono,atrim=duration=${s.seconds}`;
    args.push("-f", "lavfi", "-i", a);
  }
  const pairs = shots.map((_, i) => `[${2 * i}:v][${2 * i + 1}:a]`).join("");
  args.push("-filter_complex", `${pairs}concat=n=${shots.length}:v=1:a=1[v][a]`, "-map", "[v]", "-map", "[a]");
  args.push("-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", String(FPS), "-c:a", "aac", "-ac", "1", out);
  ff(args);
  return out;
}

export function probe(path: string): { duration: number; video: number; audio: number } {
  const out = execFileSync(
    "ffprobe",
    ["-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
    { encoding: "utf8" },
  );
  const d = JSON.parse(out) as { format: { duration: string }; streams: { codec_type: string }[] };
  return {
    duration: Number(d.format.duration),
    video: d.streams.filter((s) => s.codec_type === "video").length,
    audio: d.streams.filter((s) => s.codec_type === "audio").length,
  };
}

export function sceneCuts(path: string, threshold = 0.3): number[] {
  const err = ff(["-hide_banner", "-nostats", "-i", path, "-an", "-vf", `select='gt(scene,${threshold})',showinfo`, "-f", "null", "-"]);
  return [...err.matchAll(/pts_time:([\d.]+)/g)].map((m) => Number(m[1]));
}

export function loudnessLufs(path: string): number {
  const err = ff(["-hide_banner", "-nostats", "-i", path, "-vn", "-af", "ebur128", "-f", "null", "-"]);
  const m = /I:\s+(-?[\d.]+) LUFS/.exec(err.split("Summary:").at(-1) ?? "");
  if (!m) throw new Error("ebur128 summary not found");
  return Number(m[1]);
}

function concatArgs(src: string, cuts: Cut[], out: string | null, audioFilter: string): string[] {
  const parts = cuts.map(
    (c, i) =>
      `[0:v]trim=start=${c.start}:end=${c.end},setpts=PTS-STARTPTS[v${i}];` +
      `[0:a]atrim=start=${c.start}:end=${c.end},asetpts=PTS-STARTPTS[a${i}]`,
  );
  const pairs = cuts.map((_, i) => `[v${i}][a${i}]`).join("");
  const graph = `${parts.join(";")};${pairs}concat=n=${cuts.length}:v=1:a=1[v][a0];[a0]${audioFilter}[a]`;
  const head = ["-y", "-hide_banner", "-nostats", "-i", src, "-filter_complex", graph, "-map", "[v]", "-map", "[a]"];
  return out === null
    ? [...head, "-f", "null", "-"]
    : [...head, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", out];
}

export function render(src: string, cuts: Cut[], out: string, target = -16): string {
  const err = ff(concatArgs(src, cuts, null, `loudnorm=I=${target}:TP=-1.5:LRA=11:print_format=json`));
  const blob = /\{[^{}]*"input_i"[^{}]*\}/s.exec(err);
  if (!blob) throw new Error("loudnorm JSON not found");
  const m = JSON.parse(blob[0]) as Record<string, string>;
  const ln =
    `loudnorm=I=${target}:TP=-1.5:LRA=11:measured_I=${m.input_i}:measured_TP=${m.input_tp}` +
    `:measured_LRA=${m.input_lra}:measured_thresh=${m.input_thresh}:offset=${m.target_offset}:linear=true`;
  ff(concatArgs(src, cuts, out, ln));
  return out;
}

const HOT = new Set(["goal", "save", "penalty", "celebrating", "diving", "erupts"]);

/** Mock multimodal scorer: excitement words in transcript + caption, 0..1. */
export function score(transcript: string, caption: string): number {
  const words = `${transcript} ${caption}`.toLowerCase().split(/\s+/);
  return Math.min(1, words.filter((w) => HOT.has(w)).length / 3);
}

export function planEdl(shots: Cut[], scores: number[], budget: number, maxShot = 1.6, margin = 0.2, minScore = 0.3): Plan {
  const snap = (t: number) => Math.round(t * FPS) / FPS;
  const order = shots.map((_, i) => i).sort((a, b) => scores[b] - scores[a]);
  const chosen: EdlEntry[] = [];
  let used = 0;
  for (const i of order) {
    if (scores[i] < minScore) break;
    const srcIn = snap(shots[i].start + margin);
    const srcOut = snap(Math.min(shots[i].end - margin, srcIn + maxShot));
    const len = srcOut - srcIn;
    if (len <= 0 || used + len > budget + 1e-6) continue;
    chosen.push({ shot: i, srcIn, srcOut, score: scores[i] });
    used += len;
  }
  return { entries: chosen.sort((a, b) => a.srcIn - b.srcIn), targetLufs: -16 };
}

export const planSeconds = (p: Plan) => p.entries.reduce((s, e) => s + (e.srcOut - e.srcIn), 0);

export function verify(out: string, plan: Plan): string[] {
  const fails: string[] = [];
  const p = probe(out);
  if (Math.abs(p.duration - planSeconds(plan)) > 0.1) fails.push(`duration ${p.duration} vs ${planSeconds(plan)}`);
  if (p.video !== 1 || p.audio !== 1) fails.push(`streams v=${p.video} a=${p.audio}`);
  const lufs = loudnessLufs(out);
  if (Math.abs(lufs - plan.targetLufs) > 1) fails.push(`loudness ${lufs}`);
  const want: number[] = [];
  let t = 0;
  for (const e of plan.entries.slice(0, -1)) want.push((t += e.srcOut - e.srcIn));
  const found = sceneCuts(out);
  const bad = found.length !== want.length || found.some((f, i) => Math.abs(Math.round(f * FPS) - Math.round(want[i] * FPS)) > 1);
  if (bad) fails.push(`cut points ${found} vs ${want}`);
  return fails;
}

export function run(src: string, out: string, budget = 4): { plan: Plan; failures: string[]; trace: string[] } {
  const trace: string[] = [];
  const info = probe(src);
  const cuts = sceneCuts(src);
  const edges = [0, ...cuts, info.duration];
  const shots = edges.slice(1).map((end, i) => ({ start: edges[i], end })).filter((s) => s.end - s.start > 0.2);
  trace.push(`scene_cuts ${cuts} -> ${shots.length} shots`);
  const scores = shots.map((s, i) =>
    score(
      fixture.transcript.filter((g) => g.start < s.end && g.end > s.start).map((g) => g.text).join(" "),
      fixture.captions[i] ?? "",
    ),
  );
  const plan = planEdl(shots, scores, budget);
  trace.push(`plan ${JSON.stringify(plan.entries)}`);
  render(src, plan.entries.map((e) => ({ start: e.srcIn, end: e.srcOut })), out, plan.targetLufs);
  const failures = verify(out, plan);
  return { plan, failures, trace };
}
