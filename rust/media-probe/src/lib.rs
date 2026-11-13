//! media-probe: `probe` and `loudness` as MCP tools (rmcp 3.10.0).
//!
//! The parsing functions are pure, so they are unit-tested against fixtures. The tool methods
//! shell out to `ffprobe`/`ffmpeg`, but only for files inside a sandbox root.

use std::path::{Component, Path, PathBuf};

use rmcp::{
    Json, ServerHandler,
    handler::server::{router::tool::ToolRouter, wrapper::Parameters},
    tool, tool_handler, tool_router,
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// One stream from `ffprobe -show_streams`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
pub struct StreamInfo {
    pub codec_type: String,
    pub codec_name: String,
    pub width: Option<u32>,
    pub height: Option<u32>,
    pub sample_rate: Option<u32>,
}

/// The `probe` tool's structured output (same contract as the Python server).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
pub struct ProbeResult {
    pub path: String,
    pub duration_s: f64,
    pub streams: Vec<StreamInfo>,
}

/// The `loudness` tool's structured output.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
pub struct LoudnessResult {
    pub path: String,
    pub integrated_lufs: f64,
    pub true_peak_dbtp: f64,
}

#[derive(Debug, Deserialize, JsonSchema)]
pub struct PathArg {
    /// Path relative to the server's media root.
    pub path: String,
}

/// Parse `ffprobe -v error -show_format -show_streams -of json` output.
pub fn parse_ffprobe(path: &str, json: &str) -> Result<ProbeResult, String> {
    let v: Value = serde_json::from_str(json).map_err(|e| format!("bad ffprobe json: {e}"))?;
    let duration_s = v["format"]["duration"]
        .as_str()
        .and_then(|d| d.parse::<f64>().ok())
        .ok_or("ffprobe output has no format.duration")?;
    let num = |s: &Value, k: &str| -> Option<u32> {
        s[k].as_u64()
            .map(|n| n as u32)
            .or_else(|| s[k].as_str().and_then(|t| t.parse().ok()))
    };
    let streams = v["streams"]
        .as_array()
        .map(|a| a.as_slice())
        .unwrap_or_default()
        .iter()
        .map(|s| StreamInfo {
            codec_type: s["codec_type"].as_str().unwrap_or("unknown").to_string(),
            codec_name: s["codec_name"].as_str().unwrap_or("unknown").to_string(),
            width: num(s, "width"),
            height: num(s, "height"),
            sample_rate: num(s, "sample_rate"),
        })
        .collect();
    Ok(ProbeResult {
        path: path.to_string(),
        duration_s,
        streams,
    })
}

/// Pull the JSON block that `-af loudnorm=print_format=json` prints at the end of stderr.
pub fn parse_loudnorm(path: &str, stderr: &str) -> Result<LoudnessResult, String> {
    let start = stderr
        .rfind('{')
        .ok_or("no loudnorm json in ffmpeg output")?;
    let end = stderr[start..]
        .find('}')
        .ok_or("unterminated loudnorm json")?
        + start
        + 1;
    let v: Value =
        serde_json::from_str(&stderr[start..end]).map_err(|e| format!("bad loudnorm json: {e}"))?;
    let f = |k: &str| -> Result<f64, String> {
        v[k].as_str()
            .and_then(|s| s.parse().ok())
            .ok_or(format!("loudnorm json has no {k}"))
    };
    Ok(LoudnessResult {
        path: path.to_string(),
        integrated_lufs: f("input_i")?,
        true_peak_dbtp: f("input_tp")?,
    })
}

/// Resolve `rel` inside `root`, rejecting absolute paths and `..` (least privilege).
pub fn resolve_in_root(root: &Path, rel: &str) -> Result<PathBuf, String> {
    let p = Path::new(rel);
    if p.is_absolute() || p.components().any(|c| matches!(c, Component::ParentDir)) {
        return Err(format!("path escapes media root: {rel}"));
    }
    Ok(root.join(p))
}

#[derive(Debug, Clone)]
pub struct MediaProbe {
    root: PathBuf,
    tool_router: ToolRouter<Self>,
}

#[tool_router]
impl MediaProbe {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self {
            root: root.into(),
            tool_router: Self::tool_router(),
        }
    }

    #[tool(
        description = "Probe a media file with ffprobe: duration and streams. Read-only.",
        annotations(read_only_hint = true)
    )]
    async fn probe(
        &self,
        Parameters(arg): Parameters<PathArg>,
    ) -> Result<Json<ProbeResult>, String> {
        let file = resolve_in_root(&self.root, &arg.path)?;
        let out = tokio::process::Command::new("ffprobe")
            .args([
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
            ])
            .arg(&file)
            .output()
            .await
            .map_err(|e| format!("could not run ffprobe: {e}"))?;
        if !out.status.success() {
            return Err(format!(
                "ffprobe failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ));
        }
        parse_ffprobe(&arg.path, &String::from_utf8_lossy(&out.stdout)).map(Json)
    }

    #[tool(
        description = "Measure integrated loudness (LUFS) and true peak with ffmpeg loudnorm. Read-only.",
        annotations(read_only_hint = true)
    )]
    async fn loudness(
        &self,
        Parameters(arg): Parameters<PathArg>,
    ) -> Result<Json<LoudnessResult>, String> {
        let file = resolve_in_root(&self.root, &arg.path)?;
        let out = tokio::process::Command::new("ffmpeg")
            .args(["-hide_banner", "-nostats", "-i"])
            .arg(&file)
            .args(["-af", "loudnorm=print_format=json", "-f", "null", "-"])
            .output()
            .await
            .map_err(|e| format!("could not run ffmpeg: {e}"))?;
        if !out.status.success() {
            return Err(format!("ffmpeg failed with {}", out.status));
        }
        parse_loudnorm(&arg.path, &String::from_utf8_lossy(&out.stderr)).map(Json)
    }
}

#[tool_handler(router = self.tool_router)]
impl ServerHandler for MediaProbe {}

#[cfg(test)]
mod tests {
    use super::*;

    const FFPROBE: &str = r#"{"streams":[
      {"codec_type":"video","codec_name":"h264","width":1080,"height":2400},
      {"codec_type":"audio","codec_name":"aac","sample_rate":"48000"}],
      "format":{"duration":"12.500000"}}"#;

    #[test]
    fn parses_ffprobe() {
        let r = parse_ffprobe("a.mp4", FFPROBE).unwrap();
        assert_eq!(r.duration_s, 12.5);
        assert_eq!(r.streams[0].width, Some(1080));
        assert_eq!(r.streams[1].sample_rate, Some(48000));
    }

    #[test]
    fn parses_loudnorm_block_at_end_of_stderr() {
        let err = "[Parsed_loudnorm_0 @ 0x1] \n{\n \"input_i\" : \"-23.04\",\n \"input_tp\" : \"-5.10\",\n \"input_lra\" : \"0.00\"\n}\n";
        let r = parse_loudnorm("a.wav", err).unwrap();
        assert_eq!((r.integrated_lufs, r.true_peak_dbtp), (-23.04, -5.10));
    }

    #[test]
    fn rejects_escapes() {
        let root = Path::new("/media");
        assert!(resolve_in_root(root, "../etc/passwd").is_err());
        assert!(resolve_in_root(root, "/etc/passwd").is_err());
        assert_eq!(
            resolve_in_root(root, "clips/a.mp4").unwrap(),
            root.join("clips/a.mp4")
        );
    }
}
